import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR: Path = Path(__file__).resolve().parent
LOGS_DIR: Path = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE: Path = LOGS_DIR / "bot.log"
DB_FILE: Path = BASE_DIR / "bot.db"
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
ADMIN_ID: int = int(os.environ["ADMIN_ID"])
CF_API_TOKEN: str = os.environ["CF_API_TOKEN"]
CF_API_BASE: str = "https://api.cloudflare.com/client/v4"
PAGE_SIZE: int = 10
SUPPORTED_RECORD_TYPES: list[str] = ["A", "AAAA", "CNAME", "TXT", "MX", "SRV"]

TTL_OPTIONS: dict[str, int] = {
    "Auto (1)": 1,
    "2 min": 120,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
    "30 min": 1800,
    "1 hour": 3600,
    "2 hours": 7200,
    "5 hours": 18000,
    "12 hours": 43200,
    "1 day": 86400,
}

LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
