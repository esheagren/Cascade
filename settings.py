import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).resolve().parents[0] / "data"
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
POLY_API = os.getenv("POLY_API")
