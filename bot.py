"""
Amazon Affiliate Telegram Bot — WITH REFERRAL SYSTEM
=====================================================
Features added:
  - Every user gets a unique referral code on first /start
  - Deep links: t.me/your_bot?start=CODE → auto-credits the referrer
  - /myreferral → user sees their code, link, and progress
  - /leaderboard → top 10 referrers
  - Tier-based perks: more product results as you refer more friends
  - "📤 Share with friend" button on every product card
"""
import logging
from urllib.parse import quote
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
from referrals import (
    get_or_create_user,
    get_user_stats,
    get_user_limit,
    get_leaderboard,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------- Helpers ----------

def _build_referral_link(bot_username: str, code: str) -> str:
    """Build the t.me deep link for a referral code."""
    return f"https://t.me/{bot_username}?start={code}"


def _tier_emoji(tier: str) -> str:
    return {"standard": "🆕", "bronze": "🥉", "silver": "🥈", "gold": "🥇"}.get(tier, "🆕")


# ---------- Command Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Welcome message. Also handles referral deep links:
    /start CODE → credits the referrer with this new user.
    """
    user = update.effective_user
    args = context.args  # tokens after /start (e.g. ['ABCDEF'])
    referrer_code = args[0] if args else None

    # Create/fetch user record (credits referrer if applicable)
    stats = get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        referred_by_code=referrer_code,
    )

    # Personalize welcome message
    if stats["is_new_user"] and referrer_code:
        welcome = (
            f"👋 Hi {user.first_name}!\n\n"
            f"🎁 You joined via a friend's invite — welcome!\n\n"
            "I'm your *Amazon Shopping Assistant*. Tell me what you're looking for "
            "and I'll find the best products on Amazon for you.\n\n"
            "💬 *Try saying things like:*\n"
            "• \"Wireless mouse under 1000\"\n"
            "• \"Best protein powder for beginners\"\n"
            "• \"Gaming headphones under 3000\"\n\n"
            "💡 *Tip:* Use /myreferral to get your own invite link!"
        )
    else:
        welcome = (
            f"👋 Hi {user.first_name}!\n\n"
            "I'm your *Amazon Shopping Assistant*. Tell me what you're looking for "
            "and I'll find the best products on Amazon for you.\n\n"
            "💬 *Try saying things like:*\n"
            "• \"Wireless mouse under 1000\"\n"
            "• \"Best protein powder for beginners\"\n"
            "• \"Gift for my mom under 2000\"\n"
            "• \"Gaming headphones under 3000\"\n\n"
            "🎁 *New:* Invite friends with /myreferral and unlock premium picks!"
        )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "*How to use this bot:*\n\n"
        "🛍️ *Find products:* Just type what you want to buy\n"
        "Examples:\n"
        "• `running shoes for men under 2500`\n"
        "• `mixer grinder for indian cooking`\n"
        "• `birthday gift for 10 year old boy`\n\n"
        "*Commands:*\n"
        "/myreferral — Your invite link & rewards\n"
        "/leaderboard — Top inviters of all time\n"
        "/help — This message"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user their referral link, code, and tier progress."""
    user = update.effective_user
    # Make sure user exists in DB
    get_or_create_user(user.id, user.username, user.first_name)
    stats = get_user_stats(user.id)

    bot_username = (await context.bot.get_me()).username
    referral_link = _build_referral_link(bot_username, stats["referral_code"])

    tier_emoji = _tier_emoji(stats["tier"])
    next_tier_at = stats["next_tier_at"]

    if next_tier_at:
        progress = f"{stats['referral_count']}/{next_tier_at} to next tier"
        progress_bar = "▓" * stats["referral_count"] + "░" * (next_tier_at - stats["referral_count"])
        progress_bar = progress_bar[:next_tier_at]  # cap at 10 chars
    else:
        progress = "MAX TIER REACHED 🎉"
        progress_bar = "▓▓▓▓▓▓▓▓▓▓"

    msg = (
        f"🎁 *Your Invite Hub*\n\n"
        f"👤 Status: {tier_emoji} *{stats['tier'].upper()}*\n"
        f"👥 Friends invited: *{stats['referral_count']}*\n"
        f"📊 Progress: {progress_bar}\n"
        f"     {progress}\n\n"
        f"*🎯 Tier Rewards:*\n"
        f"🆕 Standard: 3 product picks\n"
        f"🥉 Bronze (1 invite): 4 picks\n"
        f"🥈 Silver (3 invites): 5 picks + early deals\n"
        f"🥇 Gold (10 invites): 7 picks + premium VIP access\n\n"
        f"*Your invite link:*\n"
        f"`{referral_link}`\n\n"
        f"_Tap link to copy. Send it to friends — when they join via your link, you get credited automatically!_"
    )

    # Pre-written share message for one-click sharing
    share_text = (
        f"Hey! I've been using this free Amazon shopping bot — "
        f"it suggests 3 best products based on your budget. Super useful: {referral_link}"
    )
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share with friends", url=share_url)],
        [InlineKeyboardButton("🏆 See leaderboard", callback_data="show_leaderboard")],
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def leaderboard_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top 10 referrers."""
    top = get_leaderboard(limit=10)
    if not top:
        await update.message.reply_text(
            "🏆 *Leaderboard is empty!*\n\n"
            "Be the first to invite a friend with /myreferral and claim the #1 spot!",
            parse_mode="Markdown",
        )
        return

    msg = "🏆 *Top Inviters of All Time*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(top):
        rank = medals[i] if i < 3 else f"{i+1}."
        emoji = _tier_emoji(user["tier"])
        msg += f"{rank} *{user['first_name']}* {emoji} — {user['count']} invites\n"

    msg += "\n_Want to join the leaderboard? Use /myreferral to get your invite link!_"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------- Main Message Handler ----------

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process every user message that isn't a command."""
    user_msg = update.message.text
    user = update.effective_user
    user_id = user.id

    # Make sure user is in DB
    get_or_create_user(user_id, user.username, user.first_name)

    log.info(f"User {user_id} asked: {user_msg}")
    thinking_msg = await update.message.reply_text(
        "🔍 Finding the best products for you..."
    )

    try:
        parsed = await understand_query(user_msg)
        log.info(f"Parsed query: {parsed}")

        if not parsed.get("is_shopping_query"):
            await thinking_msg.edit_text(
                "I help find products to buy. Tell me what you're shopping for! 🛍️\n\n"
                "Example: \"wireless earbuds under 2000\""
            )
            return

        # Tier-based result limit (more refers = more products)
        result_limit = get_user_limit(user_id)
        products = search_amazon_products(
            keywords=parsed["search_keywords"],
            max_price=parsed.get("max_price"),
            min_rating=parsed.get("min_rating", 4.0),
            limit=result_limit,
        )

        if not products:
            await thinking_msg.edit_text(
                "Hmm, I couldn't find products matching that. Try rephrasing? 🤔"
            )
            return

        log_query(user_id, user_msg, parsed, len(products))
        await thinking_msg.delete()

        # Tier indicator in intro for upper tiers
        stats = get_user_stats(user_id)
        tier_badge = ""
        if stats and stats["tier"] != "standard":
            tier_badge = f" {_tier_emoji(stats['tier'])}"

        intro = f"✨ Here are my top picks for *{parsed.get('category', 'your search')}*{tier_badge}:\n"
        await update.message.reply_text(intro, parse_mode="Markdown")

        # Build share text once (same product link shared with friends gets your tag)
        bot_username = (await context.bot.get_me()).username
        ref_link = _build_referral_link(bot_username, stats["referral_code"])

        for i, product in enumerate(products, 1):
            text = format_recommendation_message(i, product)
            share_msg = (
                f"Check this Amazon deal: {product['title'][:60]}\n"
                f"Found it via this free bot → {ref_link}"
            )
            share_url = f"https://t.me/share/url?url={quote(product['affiliate_url'])}&text={quote(share_msg)}"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🛒 Buy on Amazon", url=product["affiliate_url"]),
                    InlineKeyboardButton("👍", callback_data=f"like:{product['asin']}"),
                ],
                [
                    InlineKeyboardButton("📤 Share with friend", url=share_url),
                ],
            ])
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

        # Periodic referral nudge — every ~5th query
        import random
        footer_parts = [
            "_💡 Tip: Prices change. Click links to see latest._",
            "_Want more options? Just ask again!_",
        ]
        if random.random() < 0.2:  # 20% chance per query
            footer_parts.append(
                f"\n🎁 *Invite a friend* → unlock more product picks per search! Use /myreferral"
            )
        await update.message.reply_text("\n".join(footer_parts), parse_mode="Markdown")

    except Exception:
        log.exception("Error handling query")
        await thinking_msg.edit_text(
            "😔 Something went wrong. Please try again in a moment."
        )


# ---------- Button Callbacks ----------

async def button_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "show_leaderboard":
        top = get_leaderboard(limit=10)
        if not top:
            await query.message.reply_text("🏆 Leaderboard is empty! Be the first 🥇")
            return
        msg = "🏆 *Top Inviters*\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, user in enumerate(top):
            rank = medals[i] if i < 3 else f"{i+1}."
            emoji = _tier_emoji(user["tier"])
            msg += f"{rank} *{user['first_name']}* {emoji} — {user['count']} invites\n"
        await query.message.reply_text(msg, parse_mode="Markdown")
        return

    if ":" in query.data:
        action, asin = query.data.split(":", 1)
        user_id = query.from_user.id
        log_click(user_id, asin, action)
        if action == "like":
            await query.answer("Thanks! 👍", show_alert=False)


# ---------- Main ----------

def main() -> None:
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment")
    if not settings.amazon_affiliate_tag:
        raise RuntimeError("AMAZON_AFFILIATE_TAG not set in environment")

    app = Application.builder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myreferral", my_referral))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    app.add_handler(CallbackQueryHandler(button_callback))

    log.info("🤖 Bot is running with referral system. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
