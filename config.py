"""
config.py
=========
Centralized settings loaded from .env file (or Railway environment vars).
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # REQUIRED
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    amazon_affiliate_tag: str = os.getenv("AMAZON_AFFILIATE_TAG", "")

    # Market
    amazon_country: str = os.getenv("AMAZON_COUNTRY", "IN")

    # OPTIONAL — only used if you have Amazon PA-API approval
    amazon_access_key: str = os.getenv("AMAZON_ACCESS_KEY", "")
    amazon_secret_key: str = os.getenv("AMAZON_SECRET_KEY", "")


settings = Settings()
