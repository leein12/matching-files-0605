"""매칭 프로그램 설정."""

INPUT_DIR = "input"
OUTPUT_DIR = "output"
A_FILE = "A.xlsx"
B_FILE = "B.xlsx"
OUTPUT_FILE = "C.xlsx"

MATCH_THRESHOLD = 80
MAX_CANDIDATES = 5

MAX_FALLBACK_CANDIDATES = 1000

REQUIRED_COLUMNS = ["거래처키", "거래처명", "거래처주소", "전화번호"]

GENERAL_NAME_RISK_TOKENS = [
    "서울",
    "중앙",
    "제일",
    "성모",
    "우리",
    "하나",
    "행복",
    "사랑",
]

ADMIN_ALIAS = {
    ("인천", "남구"): ("인천", "미추홀구"),
}

EQUIV_MAP: dict[str, str] = {}
