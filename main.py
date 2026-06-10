"""거래처 매칭 프로그램 진입점."""

from __future__ import annotations

import sys
from pathlib import Path

import config
from matcher.excel_io import build_result_dataframe, read_input_excel, save_result_excel
from runtime_config import load_external_config


def _get_base_dir() -> Path:
    """스크립트와 PyInstaller exe 모두에서 실행 위치를 반환한다."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _pause_if_needed() -> None:
    """탐색기에서 exe 실행 시 콘솔 메시지를 확인할 수 있게 대기한다."""
    if getattr(sys, "frozen", False) and getattr(config, "PAUSE_ON_EXIT", True):
        try:
            input("\n종료하려면 Enter 키를 누르세요...")
        except EOFError:
            pass


def run() -> int:
    """메인 실행 함수."""
    base_dir = _get_base_dir()
    load_external_config(base_dir / "config.ini")

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


def main() -> int:
    """프로그램 실행 후 필요 시 종료 대기를 수행한다."""
    exit_code = run()
    _pause_if_needed()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
