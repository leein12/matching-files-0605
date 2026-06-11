"""고객명 정확일치 매핑 테스트."""

from __future__ import annotations

import pandas as pd

import config
from main import (
    MATCH_MODE_COMPANY_SIMILARITY,
    MATCH_MODE_CUSTOMER_EXACT,
    _determine_match_mode,
)
from matcher.customer_exact_matcher import (
    build_customer_exact_result_dataframe,
    has_customer_columns,
    normalize_customer_name,
)


def test_normalize_customer_name_uses_exact_clean_key():
    assert normalize_customer_name("  홍길동  ") == "홍길동"
    assert normalize_customer_name("홍  길동") == "홍 길동"
    assert normalize_customer_name("") == ""


def test_has_customer_columns_requires_both_files():
    df_a = pd.DataFrame(columns=["고객코드", "고객명"])
    df_b = pd.DataFrame(columns=["고객코드", "고객명", "거래처키"])
    assert has_customer_columns(df_a, df_b)

    df_b_missing = pd.DataFrame(columns=["고객코드"])
    assert not has_customer_columns(df_a, df_b_missing)


def test_customer_exact_result_maps_by_customer_name(monkeypatch):
    monkeypatch.setattr(config, "MAX_CANDIDATES", 2)
    df_a = pd.DataFrame(
        [
            {"고객코드": "A001", "고객명": "홍길동"},
            {"고객코드": "A002", "고객명": "김철수"},
        ]
    )
    df_b = pd.DataFrame(
        [
            {
                "고객코드": "B002",
                "고객명": "홍길동",
                "거래처키": "T002",
                "거래처명": "홍길동병원2",
                "거래처주소": "서울",
                "전화번호": "02-2222-2222",
            },
            {
                "고객코드": "B001",
                "고객명": "홍길동",
                "거래처키": "T001",
                "거래처명": "홍길동병원1",
                "거래처주소": "부산",
                "전화번호": "051-111-1111",
            },
        ]
    )

    result = build_customer_exact_result_dataframe(df_a, df_b)

    assert result.loc[0, "매칭후보수"] == 2
    assert result.loc[0, "후보1_B고객코드"] == "B001"
    assert result.loc[0, "후보1_B거래처키"] == "T001"
    assert result.loc[0, "후보2_B고객코드"] == "B002"
    assert result.loc[1, "매칭후보수"] == 0
    assert result.loc[1, "후보1_B고객명"] == ""


def test_auto_mode_selects_customer_exact_when_customer_columns_exist(monkeypatch):
    monkeypatch.setattr(config, "MATCH_MODE", "auto")
    df_a = pd.DataFrame(columns=["고객코드", "고객명"])
    df_b = pd.DataFrame(columns=["고객코드", "고객명"])
    assert _determine_match_mode(df_a, df_b) == MATCH_MODE_CUSTOMER_EXACT


def test_auto_mode_falls_back_to_company_similarity(monkeypatch):
    monkeypatch.setattr(config, "MATCH_MODE", "auto")
    df_a = pd.DataFrame(columns=["거래처키", "거래처명", "거래처주소", "전화번호"])
    df_b = pd.DataFrame(columns=["거래처키", "거래처명", "거래처주소", "전화번호"])
    assert _determine_match_mode(df_a, df_b) == MATCH_MODE_COMPANY_SIMILARITY
