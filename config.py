"""
config.py
=========
Centralized settings loaded from .env file.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # Required
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    amazon_affiliate_tag: str = os.getenv("AMAZON_AFFILIATE_TAG", "")

    # Optional (only needed if you have PA-API access)
    amazon_access_key: str = os.getenv("AMAZON_ACCESS_KEY", "")
    amazon_secret_key: str = os.getenv("AMAZON_SECRET_KEY", "")

    # Market
    amazon_country: str = os.getenv("AMAZON_COUNTRY", "IN")


settings = Settings()
