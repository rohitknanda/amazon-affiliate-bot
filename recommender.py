"""
recommender.py
==============
Uses Claude AI to:
1. Parse natural language shopping queries into structured search parameters
2. Generate friendly product recommendation messages
"""
import json
import asyncio
from anthropic import Anthropic
from config import settings

# Initialize Claude client
client = Anthropic(api_key=settings.anthropic_api_key)

# Using Haiku 4.5 — fast, cheap, perfect for this chatbot use case
# (~$1 per 1M input tokens vs $5 for Opus)
MODEL = "claude-haiku-4-5-20251001"


SYSTEM_PROMPT = """You are a product search query parser for an Amazon shopping bot.

Given a user's natural language message, extract structured search parameters.

Return ONLY a valid JSON object with these fields:
{
  "is_shopping_query": true/false,         // false if user is just chatting
  "search_keywords": "string",              // 2-5 keywords for Amazon search
  "category": "string",                     // friendly category name like "wireless mouse"
  "max_price": number or null,              // in INR, null if not specified
  "min_rating": 4.0,                        // default minimum rating
  "user_intent": "string"                   // short summary like "wants gaming mouse under 1500"
}

Examples:

User: "wireless mouse under 1000"
→ {"is_shopping_query": true, "search_keywords": "wireless mouse", "category": "wireless mouse", "max_price": 1000, "min_rating": 4.0, "user_intent": "wants wireless mouse under ₹1000"}

User: "best protein powder for beginners"
→ {"is_shopping_query": true, "search_keywords": "whey protein powder beginner", "category": "protein powder", "max_price": null, "min_rating": 4.2, "user_intent": "beginner-friendly protein powder"}

User: "diwali gift for mom under 2k"
→ {"is_shopping_query": true, "search_keywords": "gift women diwali", "category": "Diwali gift for mom", "max_price": 2000, "min_rating": 4.0, "user_intent": "Diwali gift for mom under ₹2000"}

User: "hello how are you"
→ {"is_shopping_query": false, "search_keywords": "", "category": "", "max_price": null, "min_rating": 4.0, "user_intent": "small talk"}

Output ONLY the JSON. No markdown, no explanation."""


async def understand_query(user_message: str) -> dict:
    """
    Parse user's natural language message into structured search params.
    Returns a dict — see SYSTEM_PROMPT for schema.
    """
    # Run the sync Anthropic call in a thread so it doesn't block asyncio
    def _call():
        return client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

    response = await asyncio.to_thread(_call)
    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude added any
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if Claude returns invalid JSON
        return {
            "is_shopping_query": True,
            "search_keywords": user_message,
            "category": user_message,
            "max_price": None,
            "min_rating": 4.0,
            "user_intent": user_message,
        }


def format_recommendation_message(rank: int, product: dict) -> str:
    """
    Format a single product as a clean Telegram Markdown message.
    """
    # Format price with Indian numbering
    price_str = f"₹{product['price']:,}" if product.get("price") else "Check price"

    # Rating with stars
    rating = product.get("rating", 0)
    stars = "⭐" * int(rating) if rating else ""

    # Truncate title if too long
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
