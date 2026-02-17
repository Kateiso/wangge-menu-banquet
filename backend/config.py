import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "wangge2026")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or APP_PASSWORD
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
DEFAULT_MARGIN = float(os.getenv("DEFAULT_MARGIN", "55"))
DATABASE_URL = "sqlite:///./menu.db"
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "主数据表.csv")
