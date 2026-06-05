"""엑셀 입출력."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

import config
from matcher.candidate import MatchCandidate, build_b_index, find_candidates_for_row


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _validate_columns(df: pd.DataFrame, filename: str) -> None:
    missing = [c for c in config.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{filename}에 필수 컬럼이 없습니다: {', '.join(missing)}")


def read_input_excel(path: Path) -> pd.DataFrame:
    """입력 엑셀을 읽는다."""
    if not path.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {path}")
    df = pd.read_excel(path, dtype=str)
    df = df.fillna("")
    _validate_columns(df, path.name)
    return df


def _safe_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return value


def _build_output_row(a_row: pd.Series, candidates: list[MatchCandidate]) -> dict[str, Any]:
    """결과 행을 구성한다."""
    row: dict[str, Any] = {
        "A_거래처키": _safe_value(a_row.get("거래처키", "")),
        "A_거래처명": _safe_value(a_row.get("거래처명", "")),
        "A_거래처주소": _safe_value(a_row.get("거래처주소", "")),
        "A_전화번호": _safe_value(a_row.get("전화번호", "")),
        "매칭후보수": len(candidates),
        "최고점수": candidates[0].score.total_score if candidates else "",
    }

    for i in range(1, config.MAX_CANDIDATES + 1):
        prefix = f"후보{i}"
        if i <= len(candidates):
            cand = candidates[i - 1]
            row[f"{prefix}_B거래처키"] = _safe_value(cand.b_row.get("거래처키", ""))
            row[f"{prefix}_B거래처명"] = _safe_value(cand.b_row.get("거래처명", ""))
            row[f"{prefix}_B거래처주소"] = _safe_value(cand.b_row.get("거래처주소", ""))
            row[f"{prefix}_B전화번호"] = _safe_value(cand.b_row.get("전화번호", ""))
            row[f"{prefix}_총점"] = cand.score.total_score
        else:
            row[f"{prefix}_B거래처키"] = ""
            row[f"{prefix}_B거래처명"] = ""
            row[f"{prefix}_B거래처주소"] = ""
            row[f"{prefix}_B전화번호"] = ""
            row[f"{prefix}_총점"] = ""

    return row


def get_output_columns() -> list[str]:
    """결과 파일 컬럼 순서."""
    cols = [
        "A_거래처키", "A_거래처명", "A_거래처주소", "A_전화번호",
        "매칭후보수", "최고점수",
    ]
    for i in range(1, config.MAX_CANDIDATES + 1):
        cols.extend([
            f"후보{i}_B거래처키",
            f"후보{i}_B거래처명",
            f"후보{i}_B거래처주소",
            f"후보{i}_B전화번호",
            f"후보{i}_총점",
        ])
    return cols


def build_result_dataframe(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    """A/B 데이터로 매칭 결과 DataFrame을 생성한다."""
    print(f"[INFO] A rows: {len(df_a)}, B rows: {len(df_b)}")
    print("[INFO] Normalizing B...")
    b_index = build_b_index(df_b)

    rows: list[dict[str, Any]] = []
    total = len(df_a)
    for i, (_, a_row) in enumerate(df_a.iterrows(), start=1):
        if i % 100 == 0 or i == total:
            print(f"[INFO] Matching row {i}/{total}")
        candidates = find_candidates_for_row(a_row, b_index)
        rows.append(_build_output_row(a_row, candidates))

    return pd.DataFrame(rows, columns=get_output_columns())


def _autosize_columns(ws) -> None:
    for col_idx, column_cells in enumerate(ws.columns, start=1):
        max_len = 0
        for cell in column_cells:
            val = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)


def save_result_excel(df: pd.DataFrame, path: Path) -> None:
    """결과 엑셀을 스타일과 함께 저장한다."""
    _ensure_dir(path.parent)
    numeric_cols = {"매칭후보수", "최고점수"} | {
        f"후보{i}_총점" for i in range(1, config.MAX_CANDIDATES + 1)
    }

    try:
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="매칭결과")
            ws = writer.sheets["매칭결과"]

            for cell in ws[1]:
                cell.font = Font(bold=True)

            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for col_name in numeric_cols:
                if col_name in df.columns:
                    col_idx = df.columns.get_loc(col_name) + 1
                    letter = get_column_letter(col_idx)
                    for row_idx in range(2, len(df) + 2):
                        ws[f"{letter}{row_idx}"].number_format = "0"

            _autosize_columns(ws)
    except PermissionError:
        raise PermissionError(
            f"결과 파일을 저장할 수 없습니다: {path}\n"
            "파일이 다른 프로그램(엑셀 등)에서 열려 있을 수 있습니다. "
            "파일을 닫은 후 다시 실행해 주세요."
        )
