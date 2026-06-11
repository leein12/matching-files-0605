"""매칭 프로그램 설정."""

INPUT_DIR = "input"
OUTPUT_DIR = "output"
A_FILE = "A.xlsx"
B_FILE = "B.xlsx"
OUTPUT_FILE = "C.xlsx"

MATCH_MODE = "auto"

MATCH_THRESHOLD = 0
MAX_CANDIDATES = 3
MATCH_RESULT_RANGES = [
    ("확정", 80, 100),
    ("검토", 70, 79),
    ("미매칭", 0, 69),
]

PAUSE_ON_EXIT = True

REQUIRED_COLUMNS = ["거래처키", "거래처명", "거래처주소", "전화번호"]
REQUIRED_CUSTOMER_COLUMNS = ["고객코드", "고객명"]

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
    ("경북", "군위군"): ("대구", "군위군"),
}

EQUIV_MAP: dict[str, str] = {}
