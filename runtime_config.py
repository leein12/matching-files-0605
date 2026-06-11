"""외부 설정 파일(config.ini) 로더."""

from __future__ import annotations

import configparser
from pathlib import Path

import config


DEFAULT_CONFIG_TEXT = """# 거래처 매칭 프로그램 설정 파일
# 이 파일은 메모장 등 txt 에디터로 수정할 수 있습니다.

[paths]
input_dir = input
output_dir = output
a_file = A.xlsx
b_file = B.xlsx
output_file = C.xlsx

[matching]
# auto: 고객코드/고객명 컬럼이 있으면 고객명 정확일치, 없으면 기존 유사도 매칭
# customer_exact: 고객명 100% 일치 기준 매핑
# company_similarity: 기존 거래처명+주소+전화번호 유사도 매칭
mode = auto
match_threshold = 0
max_candidates = 3
pause_on_exit = true

[result_ranges]
# 형식: 구분 = 시작점수,종료점수
확정 = 80,100
검토 = 70,79
미매칭 = 0,69

[name]
# 쉼표로 구분합니다.
general_name_risk_tokens = 서울,중앙,제일,성모,우리,하나,행복,사랑

[admin_alias]
# 형식: 원본시도|원본시군구 = 정규화시도|정규화시군구
인천|남구 = 인천|미추홀구
경북|군위군 = 대구|군위군

[equiv_map]
# 형식: 주소1 = 주소2
# 예:
# 부산 사하구 사하로186번가길 1 = 부산 사하구 사하로 188
"""


def _read_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _read_int(section: configparser.SectionProxy, key: str, default: int) -> int:
    raw = section.get(key, str(default))
    try:
        return int(raw)
    except ValueError:
        print(f"[WARN] config.ini의 {key} 값이 숫자가 아니어서 기본값 {default}을 사용합니다.")
        return default


def _read_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_result_ranges(section: configparser.SectionProxy) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    for label, raw_value in section.items():
        parts = [part.strip() for part in raw_value.split(",")]
        if len(parts) != 2:
            print(f"[WARN] result_ranges 형식 오류로 건너뜁니다: {label} = {raw_value}")
            continue
        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            print(f"[WARN] result_ranges 점수 값 오류로 건너뜁니다: {label} = {raw_value}")
            continue
        result.append((label.strip(), start, end))
    return result


def _read_pair_map(section: configparser.SectionProxy) -> dict[tuple[str, str], tuple[str, str]]:
    result: dict[tuple[str, str], tuple[str, str]] = {}
    for raw_key, raw_value in section.items():
        key_parts = [part.strip() for part in raw_key.split("|")]
        value_parts = [part.strip() for part in raw_value.split("|")]
        if len(key_parts) != 2 or len(value_parts) != 2:
            print(f"[WARN] admin_alias 형식 오류로 건너뜁니다: {raw_key} = {raw_value}")
            continue
        result[(key_parts[0], key_parts[1])] = (value_parts[0], value_parts[1])
    return result


def load_external_config(config_path: Path) -> None:
    """config.ini가 있으면 읽어서 config.py의 기본값을 덮어쓴다."""
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
        print(f"[INFO] 기본 설정 파일을 생성했습니다: {config_path}")

    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(config_path, encoding="utf-8")

    paths = parser["paths"] if parser.has_section("paths") else {}
    config.INPUT_DIR = paths.get("input_dir", config.INPUT_DIR)
    config.OUTPUT_DIR = paths.get("output_dir", config.OUTPUT_DIR)
    config.A_FILE = paths.get("a_file", config.A_FILE)
    config.B_FILE = paths.get("b_file", config.B_FILE)
    config.OUTPUT_FILE = paths.get("output_file", config.OUTPUT_FILE)

    matching = parser["matching"] if parser.has_section("matching") else {}
    config.MATCH_MODE = matching.get("mode", config.MATCH_MODE).strip().lower()
    config.MATCH_THRESHOLD = _read_int(matching, "match_threshold", config.MATCH_THRESHOLD)
    config.MAX_CANDIDATES = _read_int(matching, "max_candidates", config.MAX_CANDIDATES)
    config.PAUSE_ON_EXIT = _read_bool(
        matching.get("pause_on_exit", str(getattr(config, "PAUSE_ON_EXIT", True))),
        getattr(config, "PAUSE_ON_EXIT", True),
    )

    if parser.has_section("result_ranges"):
        ranges = _read_result_ranges(parser["result_ranges"])
        if ranges:
            config.MATCH_RESULT_RANGES = ranges

    if parser.has_section("name"):
        raw_tokens = parser["name"].get("general_name_risk_tokens", "")
        if raw_tokens.strip():
            config.GENERAL_NAME_RISK_TOKENS = _read_csv(raw_tokens)

    if parser.has_section("admin_alias"):
        config.ADMIN_ALIAS = _read_pair_map(parser["admin_alias"])

    if parser.has_section("equiv_map"):
        config.EQUIV_MAP = {
            key.strip(): value.strip()
            for key, value in parser["equiv_map"].items()
            if key.strip() and value.strip()
        }
