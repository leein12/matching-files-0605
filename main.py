"""거래처 매칭 프로그램 진입점."""

from __future__ import annotations

import sys
from pathlib import Path

import config
from matcher.excel_io import build_result_dataframe, read_input_excel, save_result_excel


def main() -> int:
    """메인 실행 함수."""
    base_dir = Path(__file__).resolve().parent
    input_dir = base_dir / config.INPUT_DIR
    output_dir = base_dir / config.OUTPUT_DIR
    a_path = input_dir / config.A_FILE
    b_path = input_dir / config.B_FILE
    output_path = output_dir / config.OUTPUT_FILE

    if not input_dir.exists():
        input_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] input 폴더를 생성했습니다: {input_dir}")
        print(f"[INFO] {config.A_FILE}, {config.B_FILE} 파일을 input 폴더에 넣어 주세요.")
        return 1

    if not a_path.exists():
        print(f"[ERROR] 입력 파일이 없습니다: {a_path}")
        print("input/A.xlsx 파일을 준비한 후 다시 실행해 주세요.")
        return 1

    if not b_path.exists():
        print(f"[ERROR] 입력 파일이 없습니다: {b_path}")
        print("input/B.xlsx 파일을 준비한 후 다시 실행해 주세요.")
        return 1

    try:
        print(f"[INFO] Reading {a_path.name}...")
        df_a = read_input_excel(a_path)
        print(f"[INFO] Reading {b_path.name}...")
        df_b = read_input_excel(b_path)

        result_df = build_result_dataframe(df_a, df_b)

        print(f"[INFO] Saving result to {output_path}...")
        save_result_excel(result_df, output_path)
        print(f"[INFO] 완료: {output_path}")
        return 0

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1
    except PermissionError as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] 처리 중 오류가 발생했습니다: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
