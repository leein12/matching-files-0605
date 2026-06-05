"""전화번호 정규화."""

from __future__ import annotations

import re
from typing import Any

_DIGIT_RE = re.compile(r"\d+")


def normalize_phone(value: Any) -> str:
    """전화번호를 숫자만 남긴 국내 형식으로 정규화한다."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""

    # 대표번호/내선 혼합 시 앞쪽 대표번호 우선
    if "/" in text:
        text = text.split("/")[0].strip()
    if "," in text:
        text = text.split(",")[0].strip()

    digits = "".join(_DIGIT_RE.findall(text))
    if not digits:
        return ""

    if digits.startswith("82") and len(digits) > 2:
        rest = digits[2:]
        if rest.startswith("10"):
            return "0" + rest
        return "0" + rest

    return digits
