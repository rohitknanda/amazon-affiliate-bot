"""
Amazon Affiliate Telegram Bot
==============================
Listens on Telegram, understands what user wants using Claude AI,
recommends Amazon products, returns them with your affiliate links.

Run with:  python bot.py
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import settings
from recommender import understand_query, format_recommendation_message
from amazon import search_amazon_products
from analytics import log_query, log_click

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------- Command Handlers ----------

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message when user types /start."""
    user = update.effective_user
    welcome = (
        f"👋 Hi {user.first_name}!\n\n"
        "I'm your *Amazon Shopping Assistant*. Tell me what you're looking for "
        "and I'll find the best products on Amazon for you.\n\n"
        "💬 *Try saying things like:*\n"
        "• \"Wireless mouse under 1000\"\n"
        "• \"Best protein powder for beginners\"\n"
        "• \"Gift for my mom under 2000\"\n"
        "• \"Gaming headphones under 3000\"\n\n"
        "Just type naturally — I'll understand! 🛍️"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """/help command."""
    msg = (
        "*How to use this bot:*\n\n"
        "Just type what you want to buy in plain English (or Hindi).\n\n"
        "Examples:\n"
        "• `running shoes for men under 2500`\n"
        "• `mixer grinder for indian cooking`\n"
        "• `birthday gift for 10 year old boy`\n\n"
        "I'll suggest 3 best options with links!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------- Main Message Handler ----------

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process every user message that isn't a command."""
    user_msg = update.message.text
    user_id = update.effective_user.id
    log.info(f"User {user_id} asked: {user_msg}")

    # Show "thinking" indicator
    thinking_msg = await update.message.reply_text(
        "🔍 Finding the best products for you..."
    )

    try:
        # Step 1: Understand what the user wants using Claude
        parsed = await understand_query(user_msg)
        log.info(f"Parsed query: {parsed}")

        if not parsed.get("is_shopping_query"):
            await thinking_msg.edit_text(
                "I help find products to buy. Tell me what you're shopping for! 🛍️\n\n"
                "Example: \"wireless earbuds under 2000\""
            )
            return

        # Step 2: Search Amazon for matching products
        products = search_amazon_products(
            keywords=parsed["search_keywords"],
            max_price=parsed.get("max_price"),
            min_rating=parsed.get("min_rating", 4.0),
            limit=3,
        )

        if not products:
            await thinking_msg.edit_text(
                "Hmm, I couldn't find products matching that. Try rephrasing? 🤔"
            )
            return

        # Step 3: Log for analytics
        log_query(user_id, user_msg, parsed, len(products))

        # Step 4: Format and send recommendations
        await thinking_msg.delete()

        intro = f"✨ Here are my top picks for *{parsed.get('category', 'your search')}*:\n"
        await update.message.reply_text(intro, parse_mode="Markdown")

        for i, product in enumerate(products, 1):
            text = format_recommendation_message(i, product)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Buy on Amazon", url=product["affiliate_url"]),
                InlineKeyboardButton("👍 Helpful", callback_data=f"like:{product['asin']}"),
            ]])
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

        # Footer
        footer = (
            "_💡 Tip: Prices and availability change. Click links to see latest._\n"
            "_Want more options? Just ask again!_"
        )
        await update.message.reply_text(footer, parse_mode="Markdown")

    except Exception as e:
        log.exception("Error handling query")
        await thinking_msg.edit_text(
            "😔 Something went wrong. Please try again in a moment."
        )


# ---------- Button Callbacks ----------

async def button_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks (like/dislike, etc)."""
    query = update.callback_query
    await query.answer()

    action, asin = query.data.split(":", 1)
    user_id = query.from_user.id
    log_click(user_id, asin, action)

    if action == "like":
        await query.answer("Thanks for the feedback! 👍", show_alert=False)


# ---------- Main ----------

def main() -> None:
    """Start the bot."""
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env file")
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env file")
    if not settings.amazon_affiliate_tag:
        raise RuntimeError("AMAZON_AFFILIATE_TAG not set in .env file")

    app = Application.builder().token(settings.telegram_token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # Free-text messages → product recommendations
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    # Button clicks
    app.add_handler(CallbackQueryHandler(button_callback))

    log.info("🤖 Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
