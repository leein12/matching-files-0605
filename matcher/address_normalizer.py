"""주소 정규화."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

import config

_SIDO_MAP = {
    "서울특별시": "서울", "서울시": "서울",
    "부산광역시": "부산", "부산시": "부산",
    "대구광역시": "대구", "대구시": "대구",
    "인천광역시": "인천", "인천시": "인천",
    "광주광역시": "광주", "광주시": "광주",
    "대전광역시": "대전", "대전시": "대전",
    "울산광역시": "울산", "울산시": "울산",
    "세종특별자치시": "세종", "세종시": "세종",
    "경기도": "경기",
    "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
}

_PAREN_RE = re.compile(r"\([^)]*\)|（[^）]*）|\[[^\]]*\]")
_WHITESPACE_RE = re.compile(r"\s+")
_FULLWIDTH_DIGIT = str.maketrans("０１２３４５６７８９", "0123456789")

_BUILDING_NOISE = [
    "메디칼타워", "빌딩", "아파트", "상가", "센터", "플라자", "타워",
    "메디컬", "오피스텔",
]

_DONG_FLOOR_HO_RE = re.compile(
    r"\b[ABCD]동\b|\b\d+동\b|\b\d+층\b|\b\d+호\b",
    re.IGNORECASE,
)

_SIGUNGU_RE = re.compile(
    r"(?:"
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남)\s+)?"
    r"(?:[가-힣]+시\s+)?[가-힣]+(?:구|군|시)"
)

_EUPMYEONDONG_RE = re.compile(r"[가-힣]+(?:읍|면|동|리|가)")

_ROAD_WITH_NUM_RE = re.compile(
    r"([가-힣]+(?:로|대로|길|번길|가길))\s*(\d+(?:-\d+)?)"
)

_ROAD_ONLY_RE = re.compile(r"([가-힣]+(?:로|대로|길|번길|가길))")


@dataclass
class AddressNormalized:
    """정규화된 주소 정보."""

    original: str
    normalized_text: str
    sido: str
    sigungu: str
    region_key: str
    eupmyeondong: str
    road_name: str
    main_no: str
    sub_no: str
    detail_removed_text: str
    flags: list[str] = field(default_factory=list)


def _to_halfwidth_digits(text: str) -> str:
    return text.translate(_FULLWIDTH_DIGIT)


def _basic_preprocess(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _to_halfwidth_digits(text)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = text.replace("·", " ").replace("ㆍ", " ")
    text = re.sub(r"[,.\u3002]", " ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _normalize_sido(text: str) -> tuple[str, str]:
    sido = ""
    for full, short in sorted(_SIDO_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if full in text:
            sido = short
            text = text.replace(full, short, 1)
            break
    if not sido:
        m = re.match(r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남)\b", text)
        if m:
            sido = m.group(1)
    return sido, text


def _apply_admin_alias(sido: str, sigungu: str) -> tuple[str, str]:
    if not sigungu:
        return sido, sigungu

    # 전주시 덕진구 통합 처리
    if "전주" in sigungu and "덕진" in sigungu:
        return "전북", "전주시 덕진구"

    key = (sido, sigungu.replace(sido, "").strip())
    if key in config.ADMIN_ALIAS:
        return config.ADMIN_ALIAS[key]

    # sigungu에 시도가 포함된 경우 분리
    for s, short in _SIDO_MAP.items():
        if sigungu.startswith(short):
            sigungu = sigungu[len(short):].strip()
            if not sido:
                sido = short
            break

    key2 = (sido, sigungu)
    if key2 in config.ADMIN_ALIAS:
        return config.ADMIN_ALIAS[key2]

    return sido, sigungu


def _remove_detail_noise(text: str) -> str:
    text = _PAREN_RE.sub(" ", text)
    text = _DONG_FLOOR_HO_RE.sub(" ", text)
    for noise in _BUILDING_NOISE:
        text = text.replace(noise, " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _parse_road_and_number(text: str) -> tuple[str, str, str, list[str]]:
    flags: list[str] = []
    road_name = ""
    main_no = ""
    sub_no = ""

    # 접합 주소: 사하로186번가길 1
    glued = re.search(
        r"([가-힣]+로\d+번(?:가길|길)|[가-힣]+로\d+|[가-힣\d]+번가길)\s*(\d+(?:-\d+)?)?",
        text,
    )
    if glued:
        raw_road = glued.group(1)
        num_part = glued.group(2) or ""
        road_name = re.sub(r"(\d+)(번(?:가길|길)?)$", r" \1\2", raw_road)
        road_name = _WHITESPACE_RE.sub(" ", road_name).strip()
        if num_part:
            parts = num_part.split("-")
            main_no = parts[0]
            sub_no = parts[1] if len(parts) > 1 else ""
        return road_name, main_no, sub_no, flags

    m = _ROAD_WITH_NUM_RE.search(text)
    if m:
        road_name = m.group(1)
        num = m.group(2)
        parts = num.split("-")
        main_no = parts[0]
        sub_no = parts[1] if len(parts) > 1 else ""
    else:
        # 접합 도로명: 동대전로81
        glued_simple = re.search(
            r"([가-힣]+(?:로|대로|길))(\d+(?:-\d+)?)",
            text,
        )
        if glued_simple:
            road_name = glued_simple.group(1)
            parts = glued_simple.group(2).split("-")
            main_no = parts[0]
            sub_no = parts[1] if len(parts) > 1 else ""
        else:
            m2 = _ROAD_ONLY_RE.search(text)
            if m2:
                road_name = m2.group(1)
                after = text[m2.end():]
                num_m = re.search(r"\s*(\d+)(?:-(\d+))?", after)
                if num_m:
                    main_no = num_m.group(1)
                    sub_no = num_m.group(2) or ""

    # 도로명 접두 동일 / 번호 근접 / 번길-본로 혼합 휴리스틱 플래그
    if road_name and re.search(r"번가길|가길", road_name):
        flags.append("branch_road_type")
    if main_no:
        flags.append("has_building_no")

    return road_name, main_no, sub_no, flags


def _extract_sigungu(text: str, sido: str) -> str:
    m = _SIGUNGU_RE.search(text)
    if not m:
        return ""
    sigungu = m.group(0).strip()
    if sido and sigungu.startswith(sido):
        sigungu = sigungu[len(sido):].strip()
    return sigungu


def _extract_eupmyeondong(text: str) -> str:
    matches = _EUPMYEONDONG_RE.findall(text)
    # 도로명에 '길'이 포함된 오탐 제거
    filtered = [m for m in matches if not m.endswith("길") and not m.endswith("로")]
    return filtered[-1] if filtered else ""


def build_region_key(sido: str, sigungu: str) -> str:
    """후보군 인덱싱용 지역 키를 생성한다."""
    if not sido or not sigungu:
        return ""
    return f"{sido}|{sigungu}"


def normalize_address(value: Any) -> AddressNormalized:
    """주소를 정규화하고 비교용 필드를 추출한다."""
    original = "" if value is None else str(value).strip()
    if original.lower() in {"nan", "none"}:
        original = ""

    text = _basic_preprocess(original)
    detail_removed = _remove_detail_noise(text)

    sido, working = _normalize_sido(detail_removed)
    sigungu = _extract_sigungu(working, sido)
    sido, sigungu = _apply_admin_alias(sido, sigungu)
    region_key = build_region_key(sido, sigungu)
    eupmyeondong = _extract_eupmyeondong(working)

    road_name, main_no, sub_no, flags = _parse_road_and_number(working)

    # 도로명 숫자 사이 공백 정리: 동대전로81 → 동대전로 + main_no=81
    if road_name:
        glued_num = re.search(r"(로|대로|길)(\d+)$", road_name)
        if glued_num and not main_no:
            road_name = road_name[: glued_num.start(2)].rstrip()
            main_no = glued_num.group(2)
        road_name = _WHITESPACE_RE.sub(" ", road_name).strip()

    normalized_text = _WHITESPACE_RE.sub(" ", working).strip()

    return AddressNormalized(
        original=original,
        normalized_text=normalized_text,
        sido=sido,
        sigungu=sigungu,
        region_key=region_key,
        eupmyeondong=eupmyeondong,
        road_name=road_name,
        main_no=main_no,
        sub_no=sub_no,
        detail_removed_text=detail_removed,
        flags=flags,
    )


def address_equiv_key(addr: AddressNormalized) -> str:
    """동등 주소 비교용 키."""
    parts = [addr.sido, addr.sigungu, addr.road_name, addr.main_no]
    if addr.sub_no:
        parts.append(addr.sub_no)
    return " ".join(p for p in parts if p).strip()
