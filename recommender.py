"""
recommender.py — GEMINI VERSION (free tier, no payment needed)
================================================================
Uses Google Gemini to parse natural language shopping queries.
Free tier: 1,500 requests/day, 15 per minute. Plenty for starting.

Get free API key: https://aistudio.google.com/apikey
"""
import json
import asyncio
import logging
import re
import google.generativeai as genai
from config import settings

log = logging.getLogger(__name__)

# Configure Gemini with your API key
genai.configure(api_key=settings.google_api_key)

# Try multiple models — first one that works wins
MODELS_TO_TRY = [
    "gemini-2.5-flash",       # Best balance (recommended)
    "gemini-2.0-flash",       # Fallback
    "gemini-1.5-flash",       # Older fallback
]

SYSTEM_PROMPT = """You are a product search query parser for an Amazon shopping bot.

Given a user's message, extract structured search parameters.

Return ONLY a valid JSON object with these fields:
{
  "is_shopping_query": true/false,
  "search_keywords": "string",
  "category": "string",
  "max_price": number or null,
  "min_rating": 4.0,
  "user_intent": "string"
}

Examples:

User: "wireless mouse under 1000"
{"is_shopping_query": true, "search_keywords": "wireless mouse", "category": "wireless mouse", "max_price": 1000, "min_rating": 4.0, "user_intent": "wants wireless mouse under 1000"}

User: "best protein powder for beginners"
{"is_shopping_query": true, "search_keywords": "whey protein powder beginner", "category": "protein powder", "max_price": null, "min_rating": 4.2, "user_intent": "beginner protein"}

User: "diwali gift for mom under 2k"
{"is_shopping_query": true, "search_keywords": "gift women diwali", "category": "Diwali gift for mom", "max_price": 2000, "min_rating": 4.0, "user_intent": "Diwali gift for mom under 2000"}

User: "hello"
{"is_shopping_query": false, "search_keywords": "", "category": "", "max_price": null, "min_rating": 4.0, "user_intent": "small talk"}

Output ONLY the JSON. No markdown, no code fences, no explanation."""


async def understand_query(user_message: str) -> dict:
    """Parse user's message into search params using Gemini."""
    last_error = None

    for model_name in MODELS_TO_TRY:
        try:
            log.info(f"Trying Gemini model: {model_name}")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
            )

            def _call():
                return model.generate_content(
                    user_message,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 400,
                        "response_mime_type": "application/json",
                    },
                )

            response = await asyncio.to_thread(_call)
            raw = response.text.strip()
            log.info(f"✅ Gemini {model_name} worked")

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)

        except Exception as e:
            log.warning(f"❌ Gemini {model_name} failed: {type(e).__name__}: {str(e)[:200]}")
            last_error = e
            continue

    # All AI models failed — regex fallback so bot still works
    log.error(f"All Gemini models failed. Last error: {last_error}")
    log.info("Using regex-based keyword fallback")

    max_price = _extract_price(user_message)
    keywords = _clean_keywords(user_message)
    return {
        "is_shopping_query": True,
        "search_keywords": keywords,
        "category": keywords,
        "max_price": max_price,
        "min_rating": 4.0,
        "user_intent": user_message,
    }


def _extract_price(text: str) -> int | None:
    """Pull price like 'under 1500' or '2k' from text."""
    text_lower = text.lower()

    match = re.search(
        r"(?:under|below|less than|for|max|upto|up to|<=?)\s*(\d+)\s*(k)?",
        text_lower,
    )
    if match:
        num = int(match.group(1))
        if match.group(2) == "k":
            num *= 1000
        return num

    match = re.search(r"\b(\d+)\s*k\b", text_lower)
    if match:
        return int(match.group(1)) * 1000

    match = re.search(r"\b(\d{3,5})\b", text_lower)
    if match:
        return int(match.group(1))

    return None


def _clean_keywords(text: str) -> str:
    """Remove price phrases to get clean search keywords."""
    cleaned = re.sub(
        r"(under|below|less than|for|max|upto|up to|≤|<=?)\s*\d+\s*k?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d+\s*k?\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def format_recommendation_message(rank: int, product: dict) -> str:
    """Format a product card for Telegram."""
    price_str = f"₹{product['price']:,}" if product.get("price") else "Check price on Amazon"
    rating = product.get("rating", 0)
    stars = "⭐" * int(rating) if rating else ""

    title = product["title"]
    if len(title) > 100:
        title = title[:97] + "..."

    msg = f"*#{rank}. {title}*\n\n"
    msg += f"💰 *Price:* {price_str}\n"
    if rating:
        msg += f"{stars} *{rating}/5* ({product.get('review_count', 'N/A')} reviews)\n"
    if product.get("highlight"):
        msg += f"\n✨ _{product['highlight']}_\n"

    return msg
