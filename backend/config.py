import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "wangge2026")
DEFAULT_MARGIN = float(os.getenv("DEFAULT_MARGIN", "55"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
DATABASE_URL = "sqlite:///./menu.db"
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "主数据表.csv")
