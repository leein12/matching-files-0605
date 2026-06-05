"""점수 계산."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

import config
from matcher.address_normalizer import AddressNormalized, address_equiv_key
from matcher.name_normalizer import NameNormalized


@dataclass
class ScoreDetail:
    """내부 점수 상세 (결과 파일에 출력하지 않음)."""

    name_score: float
    address_score: float
    phone_bonus: float
    total_score: float


def _base_key_match_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 20.0
    if a in b or b in a:
        return 12.0
    return 0.0


def _string_similarity_score(a_text: str, b_text: str) -> float:
    if not a_text or not b_text:
        return 0.0
    token_score = fuzz.token_sort_ratio(a_text, b_text) / 100 * 10
    partial_score = fuzz.partial_ratio(a_text, b_text) / 100 * 5
    return token_score + partial_score


def _chosung_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 8.0
    ratio = fuzz.ratio(a, b)
    if ratio >= 90:
        return 6.0
    if ratio >= 80:
        return 4.0
    return 0.0


def _same_numbers_bonus(a_nums: list[str], b_nums: list[str]) -> float:
    if not a_nums or not b_nums:
        return 0.0
    if set(a_nums) == set(b_nums):
        return 2.0
    if set(a_nums) & set(b_nums):
        return 1.0
    return 0.0


def _is_general_name_risk(base_key: str) -> bool:
    if not base_key:
        return False
    return any(token in base_key for token in config.GENERAL_NAME_RISK_TOKENS)


def calc_name_score(
    a_name: NameNormalized,
    b_name: NameNormalized,
    a_addr: AddressNormalized | None = None,
    b_addr: AddressNormalized | None = None,
) -> float:
    """거래처명 점수 (최대 50점)."""
    score = 0.0
    score += _base_key_match_score(a_name.base_key, b_name.base_key)
    score += _string_similarity_score(a_name.normalized_text, b_name.normalized_text)
    score += _chosung_score(a_name.chosung_key, b_name.chosung_key)

    score += _same_numbers_bonus(a_name.numbers, b_name.numbers)

    if a_name.has_univ and b_name.has_univ:
        score += 1.0
    if a_name.has_affiliate and b_name.has_affiliate:
        score += 1.0
    if a_name.has_univ and b_name.has_univ and a_name.has_affiliate and b_name.has_affiliate:
        score += 2.0

    if a_name.is_health_agency and b_name.is_health_agency:
        a_tokens = set(a_name.health_sigungu_tokens)
        b_tokens = set(b_name.health_sigungu_tokens)
        if a_tokens and b_tokens and a_tokens & b_tokens:
            score += 3.0

    if _is_general_name_risk(a_name.base_key) and _is_general_name_risk(b_name.base_key):
        if a_name.base_key == b_name.base_key:
            score -= 3.0
            if a_addr and b_addr and a_addr.sigungu and b_addr.sigungu:
                if a_addr.sigungu != b_addr.sigungu:
                    score -= 2.0

    # 동일 원본명은 높은 유사도 보장
    if a_name.original and a_name.original == b_name.original:
        score = max(score, 42.0)

    return max(0.0, min(50.0, score))


def _sigungu_match(a: AddressNormalized, b: AddressNormalized) -> bool:
    if not a.sigungu or not b.sigungu:
        return False
    if a.sigungu == b.sigungu:
        return True
    a_sido, a_sig = config.ADMIN_ALIAS.get((a.sido, a.sigungu), (a.sido, a.sigungu))
    b_sido, b_sig = config.ADMIN_ALIAS.get((b.sido, b.sigungu), (b.sido, b.sigungu))
    return a_sido == b_sido and a_sig == b_sig


def calc_address_score(a: AddressNormalized, b: AddressNormalized) -> float:
    """주소 점수 (최대 50점)."""
    # EQUIV_MAP 동등 주소
    key_a = address_equiv_key(a)
    key_b = address_equiv_key(b)
    if key_a and key_b:
        canon_a = config.EQUIV_MAP.get(key_a, key_a)
        canon_b = config.EQUIV_MAP.get(key_b, key_b)
        if canon_a == canon_b:
            return 50.0

    score = 0.0
    sigungu_diff = bool(a.sigungu and b.sigungu and not _sigungu_match(a, b))

    if a.sido and b.sido and a.sido == b.sido:
        score += 8.0

    if _sigungu_match(a, b):
        score += 12.0
    elif sigungu_diff:
        score += 0.0  # 시군구 점수 0

    if a.eupmyeondong and b.eupmyeondong and a.eupmyeondong == b.eupmyeondong:
        score += 5.0

    if a.road_name and b.road_name:
        if a.road_name == b.road_name:
            score += 15.0
        else:
            ratio = fuzz.ratio(a.road_name, b.road_name)
            if ratio >= 90:
                score += 12.0
            elif ratio >= 80:
                score += 8.0

    if a.main_no and b.main_no:
        if a.main_no == b.main_no:
            score += 8.0
            if a.sub_no and b.sub_no and a.sub_no == b.sub_no:
                score += 2.0
        else:
            try:
                diff = abs(int(a.main_no) - int(b.main_no))
                if diff == 1:
                    score += 4.0
                elif diff == 2:
                    score += 2.0
            except ValueError:
                pass

    # 괄호 정보만 다른 경우 보너스
    if (
        a.road_name and b.road_name
        and a.road_name == b.road_name
        and a.main_no and b.main_no
        and a.main_no == b.main_no
        and a.original != b.original
    ):
        score += 3.0

    score = min(50.0, score)

    if sigungu_diff:
        score = min(score, 25.0)

    # 행정구역 정보가 거의 없으면 보수적 계산
    if not a.sido and not a.sigungu and not b.sido and not b.sigungu:
        score = min(score, 30.0)

    return max(0.0, score)


def calc_phone_bonus(a_phone: str, b_phone: str) -> float:
    """전화번호 가점 (최대 20점)."""
    if not a_phone or not b_phone:
        return 0.0
    if a_phone == b_phone:
        return 20.0
    if len(a_phone) >= 8 and len(b_phone) >= 8 and a_phone[-8:] == b_phone[-8:]:
        return 10.0
    return 0.0


def calc_total_score(
    a_name: NameNormalized,
    b_name: NameNormalized,
    a_addr: AddressNormalized,
    b_addr: AddressNormalized,
    a_phone: str,
    b_phone: str,
) -> ScoreDetail:
    """최종 점수 계산."""
    name_score = calc_name_score(a_name, b_name, a_addr, b_addr)
    address_score = calc_address_score(a_addr, b_addr)
    phone_bonus = calc_phone_bonus(a_phone, b_phone)
    total = min(100.0, name_score + address_score + phone_bonus)
    return ScoreDetail(
        name_score=name_score,
        address_score=address_score,
        phone_bonus=phone_bonus,
        total_score=total,
    )


def name_score_grade(name_score: float) -> str:
    """내부 등급 (결과 파일 미출력)."""
    if name_score >= 42:
        return "높음"
    if name_score >= 35:
        return "애매함"
    return "낮음"
