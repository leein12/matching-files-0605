"""고객명 정확일치 기반 매핑."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

import config

CUSTOMER_COLUMNS = ["고객코드", "고객명"]
B_DISPLAY_COLUMNS = ["고객코드", "고객명", "거래처키", "거래처명", "거래처주소", "전화번호"]

_WHITESPACE_RE = re.compile(r"\s+")


def has_customer_columns(df_a: pd.DataFrame, df_b: pd.DataFrame) -> bool:
    """A/B 양쪽에 고객코드, 고객명 컬럼이 모두 있는지 확인한다."""
    return all(col in df_a.columns for col in CUSTOMER_COLUMNS) and all(
        col in df_b.columns for col in CUSTOMER_COLUMNS
    )


def normalize_customer_name(value: Any) -> str:
    """고객명 정확일치 비교용 키를 만든다."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _safe_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else value


def _build_b_index(df_b: pd.DataFrame) -> dict[str, list[pd.Series]]:
    index: dict[str, list[pd.Series]] = {}
    for _, row in df_b.iterrows():
        key = normalize_customer_name(row.get("고객명", ""))
        if key:
            index.setdefault(key, []).append(row)

    for rows in index.values():
        rows.sort(key=lambda row: str(row.get("고객코드", "")))
    return index


def get_customer_exact_output_columns() -> list[str]:
    """고객명 정확일치 결과 컬럼 순서."""
    cols = ["A_고객코드", "A_고객명", "매칭후보수"]
    for i in range(1, config.MAX_CANDIDATES + 1):
        prefix = f"후보{i}"
        cols.extend(
            [
                f"{prefix}_B고객코드",
                f"{prefix}_B고객명",
                f"{prefix}_B거래처키",
                f"{prefix}_B거래처명",
                f"{prefix}_B거래처주소",
                f"{prefix}_B전화번호",
            ]
        )
    return cols


def _build_output_row(a_row: pd.Series, matches: list[pd.Series]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "A_고객코드": _safe_value(a_row.get("고객코드", "")),
        "A_고객명": _safe_value(a_row.get("고객명", "")),
        "매칭후보수": len(matches),
    }

    displayed = matches[: config.MAX_CANDIDATES]
    for i in range(1, config.MAX_CANDIDATES + 1):
        prefix = f"후보{i}"
        if i <= len(displayed):
            b_row = displayed[i - 1]
            row[f"{prefix}_B고객코드"] = _safe_value(b_row.get("고객코드", ""))
            row[f"{prefix}_B고객명"] = _safe_value(b_row.get("고객명", ""))
            row[f"{prefix}_B거래처키"] = _safe_value(b_row.get("거래처키", ""))
            row[f"{prefix}_B거래처명"] = _safe_value(b_row.get("거래처명", ""))
            row[f"{prefix}_B거래처주소"] = _safe_value(b_row.get("거래처주소", ""))
            row[f"{prefix}_B전화번호"] = _safe_value(b_row.get("전화번호", ""))
        else:
            row[f"{prefix}_B고객코드"] = ""
            row[f"{prefix}_B고객명"] = ""
            row[f"{prefix}_B거래처키"] = ""
            row[f"{prefix}_B거래처명"] = ""
            row[f"{prefix}_B거래처주소"] = ""
            row[f"{prefix}_B전화번호"] = ""
    return row


def build_customer_exact_result_dataframe(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
) -> pd.DataFrame:
    """고객명이 정확히 일치하는 B 후보를 A 행 우측에 붙인다."""
    print(f"[INFO] A rows: {len(df_a)}, B rows: {len(df_b)}")
    print("[INFO] Matching mode: customer_exact")
    print("[INFO] Building customer name index for B...")
    b_index = _build_b_index(df_b)

    rows: list[dict[str, Any]] = []
    total = len(df_a)
    for i, (_, a_row) in enumerate(df_a.iterrows(), start=1):
        if i % 100 == 0 or i == total:
            print(f"[INFO] Matching row {i}/{total}")
        key = normalize_customer_name(a_row.get("고객명", ""))
        matches = b_index.get(key, []) if key else []
        rows.append(_build_output_row(a_row, matches))

    return pd.DataFrame(rows, columns=get_customer_exact_output_columns())
