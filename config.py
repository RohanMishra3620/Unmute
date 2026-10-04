import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _contacts(raw):
    out = []
    for part in raw.split(";"):
        if ":" in part:
            label, number = part.rsplit(":", 1)
            if label.strip() and number.strip():
                out.append({"label": label.strip(), "number": number.strip()})
    return out


class Config:
    APP_NAME = "Unmute"
    DB_PATH = os.getenv("DB_PATH") or os.path.join(BASE_DIR, "unmute.db")
    SESSION_SECONDS = int(os.getenv("SESSION_SECONDS") or 300)
    MAX_MESSAGE_CHARS = 1000
    PORT = int(os.getenv("PORT") or 5000)
    LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").split()[0].lower()
    LLM_API_KEY = os.getenv("LLM_API_KEY") or ""
    LLM_MODEL = os.getenv("LLM_MODEL") or ""
    LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT") or 12)
    EMERGENCY_MESSAGE = os.getenv("EMERGENCY_MESSAGE") or (
        "If you are in immediate danger or think you may hurt yourself or someone else, contact your "
        "local emergency service or go to the nearest emergency department. If possible, stay with someone you trust."
    )
    EMERGENCY_CONTACTS = _contacts(os.getenv("EMERGENCY_CONTACTS") or "Emergency services:112;Tele-MANAS (India):14416")

    @classmethod
    def as_dict(cls):
        return {k: v for k, v in vars(cls).items() if k.isupper()}
