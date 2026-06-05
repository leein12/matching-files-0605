"""거래처명 정규화."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# 한글 초성
_CHOSUNG = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]
_CHOSUNG_BASE = ord("가")
_CHOSUNG_INTERVAL = 588

_SPECIAL_CHARS_RE = re.compile(r"[./&·ㆍ_\-]")
_PAREN_RE = re.compile(r"\([^)]*\)|（[^）]*）|\[[^\]]*\]|【[^】]*】|〈[^〉]*〉|「[^」]*」")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_KO_RE = re.compile(r"[^0-9a-zA-Z가-힣]")

_LEGAL_ENTITY_TOKENS = [
    "의료법인", "학교법인", "재단법인", "사회복지법인", "사단법인",
    "유지재단", "복지재단", "의료재단", "의료생협", "법인", "재단", "의료",
    "의)", "(의)",
]

_BRANCH_SUFFIXES = [
    "고양점", "제천점", "분원", "캠퍼스", "지점", "본점", "별관", "신관",
]

_TYPE_TOKENS = ["요양병원", "재활병원", "의학원", "의료원", "병원", "의원", "센터"]

_SIDO_PATTERNS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "전북특별자치도",
    "강원특별자치도", "서울시", "부산시", "대구시", "인천시", "광주시",
    "대전시", "울산시", "세종시", "경기도", "강원도", "충청북도", "충청남도",
    "전라북도", "전라남도", "경상북도", "경상남도",
]

_HEALTH_AGENCY_TYPES = ["보건소", "보건지소", "건강지원센터"]

_AUX_KEYWORDS = ["국립", "보훈", "대학교", "부속", "대학"]


@dataclass
class NameNormalized:
    """정규화된 거래처명 정보."""

    original: str
    normalized_text: str
    base_key: str
    aux_key: str
    chosung_key: str
    numbers: list[str]
    has_univ: bool
    has_affiliate: bool
    is_health_agency: bool
    health_sigungu_tokens: list[str]


def _to_halfwidth(text: str) -> str:
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            result.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


def _basic_preprocess(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _to_halfwidth(text)
    text = text.strip()
    text = _SPECIAL_CHARS_RE.sub(" ", text)
    text = _PAREN_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _apply_synonyms(text: str) -> str:
    replacements = [
        ("카톨릭학원", "가톨릭학원"),
        ("카톨릭", "가톨릭"),
        ("세브랑스", "세브란스"),
        ("의과대학", "의과대학"),
        ("의대", "의과대학"),
        ("부설병원", "부속"),
        ("부속병원", "부속"),
        ("부설", "부속"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # 이미 '대학교'인 경우 중복 치환 방지
    text = re.sub(r"대학(?!교)", "대학교", text)
    return text


def _remove_tokens(text: str, tokens: list[str]) -> str:
    for token in sorted(tokens, key=len, reverse=True):
        text = text.replace(token, " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _extract_numbers(text: str) -> list[str]:
    return re.findall(r"\d+", text)


def _extract_chosung(text: str) -> str:
    result = []
    for ch in text:
        if "가" <= ch <= "힣":
            idx = (ord(ch) - _CHOSUNG_BASE) // _CHOSUNG_INTERVAL
            if 0 <= idx < len(_CHOSUNG):
                result.append(_CHOSUNG[idx])
    return "".join(result)


def _is_health_agency(text: str) -> bool:
    return any(t in text for t in _HEALTH_AGENCY_TYPES)


def _process_health_agency(text: str) -> tuple[str, list[str]]:
    """보건소/보건지소/건강지원센터는 시군구+기관유형 중심으로 유지."""
    agency_type = ""
    for t in _HEALTH_AGENCY_TYPES:
        if t in text:
            agency_type = t
            break

    working = text
    for sido in _SIDO_PATTERNS:
        working = working.replace(sido, " ")

    # 시/군/구 토큰 추출
    tokens = _WHITESPACE_RE.sub(" ", working).strip().split()
    sigungu_tokens = [t for t in tokens if t != agency_type]
    compact = "".join(sigungu_tokens) + agency_type
    return compact, sigungu_tokens


def _build_base_key(text: str) -> str:
    text = _NON_ALNUM_KO_RE.sub("", text)
    text = text.lower()
    return text.replace(" ", "")


def _build_aux_key(base_key: str, source_text: str) -> str:
    extras: list[str] = []
    for kw in _AUX_KEYWORDS:
        if kw in source_text:
            extras.append(kw.replace(" ", ""))

    # 도시명/캠퍼스명 등 간단 추출
    campus_match = re.search(r"([가-힣]+캠퍼스)", source_text)
    if campus_match:
        extras.append(campus_match.group(1).replace(" ", ""))

    city_match = re.search(r"([가-힣]+시)(?![가-힣]*구)", source_text)
    if city_match and "보건" not in source_text:
        extras.append(city_match.group(1))

    return base_key + "".join(extras)


def normalize_name(value: Any) -> NameNormalized:
    """거래처명을 정규화하고 비교용 키를 생성한다."""
    original = "" if value is None else str(value).strip()
    if original.lower() in {"nan", "none"}:
        original = ""

    text = _basic_preprocess(original)
    text = _apply_synonyms(text)
    text = _remove_tokens(text, _LEGAL_ENTITY_TOKENS)
    text = _remove_tokens(text, _BRANCH_SUFFIXES)

    numbers = _extract_numbers(text)
    has_univ = "대학교" in text or "대학" in text
    has_affiliate = "부속" in text

    health_sigungu_tokens: list[str] = []
    is_health = _is_health_agency(text)

    if is_health:
        compact, health_sigungu_tokens = _process_health_agency(text)
        working = compact
    else:
        working = text
        for sido in _SIDO_PATTERNS:
            working = working.replace(sido, " ")

    working = _remove_tokens(working, _TYPE_TOKENS)
    working = _WHITESPACE_RE.sub("", working)

    base_key = _build_base_key(working)
    aux_key = _build_aux_key(base_key, text)
    chosung_key = _extract_chosung(working)

    return NameNormalized(
        original=original,
        normalized_text=text,
        base_key=base_key,
        aux_key=aux_key,
        chosung_key=chosung_key,
        numbers=numbers,
        has_univ=has_univ,
        has_affiliate=has_affiliate,
        is_health_agency=is_health,
        health_sigungu_tokens=health_sigungu_tokens,
    )
