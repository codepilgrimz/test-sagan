import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD", "changeme")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "portal.db"))

Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
