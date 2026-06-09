"""후보군 축소 및 매칭."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

import config
from matcher.address_normalizer import AddressNormalized, normalize_address
from matcher.name_normalizer import NameNormalized, normalize_name
from matcher.phone_normalizer import normalize_phone
from matcher.scoring import ScoreDetail, calc_name_score, calc_total_score


@dataclass
class BRecord:
    """정규화된 B 행."""

    index: int
    row: pd.Series
    name: NameNormalized
    address: AddressNormalized
    phone: str


@dataclass
class MatchCandidate:
    """매칭 후보."""

    b_index: int
    b_row: pd.Series
    score: ScoreDetail


@dataclass
class BIndex:
    """B 후보군 인덱스."""

    records: list[BRecord]
    by_region: dict[str, list[int]]
    by_sido: dict[str, list[int]]
    by_name_prefix: dict[str, list[int]]


def _safe_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def build_b_index(df_b: pd.DataFrame) -> BIndex:
    """B 데이터를 정규화하고 인덱스를 구축한다."""
    records: list[BRecord] = []
    by_region: dict[str, list[int]] = {}
    by_sido: dict[str, list[int]] = {}
    by_name_prefix: dict[str, list[int]] = {}

    for idx, row in df_b.iterrows():
        name = normalize_name(row["거래처명"])
        address = normalize_address(row["거래처주소"])
        phone = normalize_phone(row["전화번호"])

        rec = BRecord(index=int(idx), row=row, name=name, address=address, phone=phone)
        records.append(rec)
        pos = len(records) - 1

        if address.region_key:
            by_region.setdefault(address.region_key, []).append(pos)
        if address.sido:
            by_sido.setdefault(address.sido, []).append(pos)

        prefix = _name_prefix_key(name.base_key)
        if prefix:
            by_name_prefix.setdefault(prefix, []).append(pos)

    return BIndex(
        records=records,
        by_region=by_region,
        by_sido=by_sido,
        by_name_prefix=by_name_prefix,
    )


def _name_prefix_key(base_key: str) -> str:
    if not base_key:
        return ""
    if base_key[0].isdigit():
        m = re.match(r"\d+", base_key)
        return m.group(0) if m else base_key[:2]
    return base_key[:2]


def _collect_indices(
    b_index: BIndex,
    a_name: NameNormalized,
    a_addr: AddressNormalized,
    fallback_all: bool,
) -> list[int]:
    """후보군 인덱스를 단계적으로 확장한다."""
    seen: set[int] = set()
    result: list[int] = []

    def add_from(bucket: dict[str, list[int]], key: str) -> None:
        for pos in bucket.get(key, []):
            if pos not in seen:
                seen.add(pos)
                result.append(pos)

    # 1. 동일 시도+시군구
    if a_addr.region_key:
        add_from(b_index.by_region, a_addr.region_key)

    # 2. 동일 시도
    if not result and a_addr.sido:
        add_from(b_index.by_sido, a_addr.sido)

    # 3. 거래처명 base_key 앞 2글자/숫자
    if not result:
        prefix = _name_prefix_key(a_name.base_key)
        if prefix:
            add_from(b_index.by_name_prefix, prefix)

    # 4. 전체 fallback
    if not result or fallback_all:
        for pos in range(len(b_index.records)):
            if pos not in seen:
                seen.add(pos)
                result.append(pos)

    if len(result) > config.MAX_FALLBACK_CANDIDATES:
        result = result[: config.MAX_FALLBACK_CANDIDATES]

    return result


def find_candidates_for_row(
    a_row: pd.Series,
    b_index: BIndex,
    *,
    fallback_all: bool = False,
) -> list[MatchCandidate]:
    """A 한 행에 대한 매칭 후보를 찾는다."""
    a_name = normalize_name(a_row["거래처명"])
    a_addr = normalize_address(a_row["거래처주소"])
    a_phone = normalize_phone(a_row["전화번호"])

    candidate_positions = _collect_indices(b_index, a_name, a_addr, fallback_all)
    is_full_fallback = len(candidate_positions) >= len(b_index.records) * 0.5

    candidates: list[MatchCandidate] = []
    for pos in candidate_positions:
        b_rec = b_index.records[pos]

        if is_full_fallback:
            prelim_name = calc_name_score(a_name, b_rec.name, a_addr, b_rec.address)
            if prelim_name < 20:
                continue

        score = calc_total_score(
            a_name, b_rec.name, a_addr, b_rec.address, a_phone, b_rec.phone
        )
        if score.total_score >= config.MATCH_THRESHOLD:
            candidates.append(
                MatchCandidate(b_index=b_rec.index, b_row=b_rec.row, score=score)
            )

    candidates.sort(
        key=lambda c: (
            -c.score.total_score,
            -c.score.address_score,
            -c.score.name_score,
            -c.score.phone_bonus,
            _safe_str(c.b_row.get("거래처키", "")),
        )
    )
    return candidates[: config.MAX_CANDIDATES]
