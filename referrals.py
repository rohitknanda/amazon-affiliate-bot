"""
referrals.py
============
Referral system for the Amazon affiliate bot.

How it works:
  1. Every user gets a unique referral code (e.g. ABCDEF)
  2. They share link: https://t.me/your_bot?start=ABCDEF
  3. New user clicks → bot extracts ABCDEF from /start command
  4. We track: who referred whom + how many referrals each user has
  5. After N referrals → user unlocks perks (more results, premium picks, etc.)

Uses SQLite (same DB as analytics.py — bot_analytics.db).
"""
import sqlite3
import logging
import random
import string
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger(__name__)
DB_FILE = "bot_analytics.db"

# Perk tiers — unlock features as users refer more friends
TIER_BRONZE = 1   # 1 referral → bronze
TIER_SILVER = 3   # 3 referrals → silver (e.g. 5 product results instead of 3)
TIER_GOLD = 10    # 10 referrals → gold (premium picks, early access to deals)


def init_referrals_db():
    """Create referral tables on first run."""
    with _conn() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referral_code TEXT UNIQUE NOT NULL,
                referred_by_code TEXT,
                referral_count INTEGER DEFAULT 0,
                tier TEXT DEFAULT 'standard',
                joined_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_referral_code ON users(referral_code)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                new_user_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(new_user_id)
            )
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def _generate_unique_code() -> str:
    """Generate a 6-character referral code that's not already in use."""
    for _ in range(10):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        with _conn() as cur:
            existing = cur.execute(
                "SELECT 1 FROM users WHERE referral_code = ?", (code,)
            ).fetchone()
            if not existing:
                return code
    # Extremely unlikely fallback
    raise RuntimeError("Could not generate unique referral code")


def get_or_create_user(
    user_id: int,
    username: str | None,
    first_name: str | None,
    referred_by_code: str | None = None,
) -> dict:
    """
    Get user record, creating one if they're new.
    If referred_by_code is provided AND this is a new user, credit the referrer.
    Returns dict with: referral_code, referral_count, tier, is_new_user
    """
    with _conn() as cur:
        existing = cur.execute(
            "SELECT referral_code, referral_count, tier FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if existing:
            return {
                "referral_code": existing[0],
                "referral_count": existing[1],
                "tier": existing[2],
                "is_new_user": False,
            }

        # New user — generate their code
        new_code = _generate_unique_code()

        # Validate referrer code (if any) and prevent self-referral
        valid_referrer_code = None
        referrer_id = None
        if referred_by_code:
            referrer = cur.execute(
                "SELECT user_id FROM users WHERE referral_code = ?",
                (referred_by_code.upper(),),
            ).fetchone()
            if referrer and referrer[0] != user_id:
                valid_referrer_code = referred_by_code.upper()
                referrer_id = referrer[0]

        # Insert new user
        cur.execute(
            "INSERT INTO users (user_id, username, first_name, referral_code, referred_by_code, joined_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user_id,
                username or "",
                first_name or "",
                new_code,
                valid_referrer_code,
                datetime.utcnow().isoformat(),
            ),
        )

        # Credit the referrer if valid
        if referrer_id:
            try:
                cur.execute(
                    "INSERT INTO referral_events (referrer_id, new_user_id, timestamp) "
                    "VALUES (?, ?, ?)",
                    (referrer_id, user_id, datetime.utcnow().isoformat()),
                )
                cur.execute(
                    "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                    (referrer_id,),
                )
                # Bump tier if needed
                new_count = cur.execute(
                    "SELECT referral_count FROM users WHERE user_id = ?",
                    (referrer_id,),
                ).fetchone()[0]
                new_tier = _calculate_tier(new_count)
                cur.execute(
                    "UPDATE users SET tier = ? WHERE user_id = ?",
                    (new_tier, referrer_id),
                )
                log.info(f"User {user_id} was referred by {referrer_id}")
            except sqlite3.IntegrityError:
                pass  # already credited

        return {
            "referral_code": new_code,
            "referral_count": 0,
            "tier": "standard",
            "is_new_user": True,
        }


def _calculate_tier(referral_count: int) -> str:
    """Determine tier based on referral count."""
    if referral_count >= TIER_GOLD:
        return "gold"
    elif referral_count >= TIER_SILVER:
        return "silver"
    elif referral_count >= TIER_BRONZE:
        return "bronze"
    return "standard"


def get_user_stats(user_id: int) -> dict | None:
    """Get a user's referral stats. Returns None if user doesn't exist."""
    with _conn() as cur:
        row = cur.execute(
            "SELECT referral_code, referral_count, tier FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "referral_code": row[0],
            "referral_count": row[1],
            "tier": row[2],
            "next_tier_at": _next_tier_threshold(row[1]),
        }


def _next_tier_threshold(current_count: int) -> int | None:
    """How many more referrals until next tier?"""
    if current_count < TIER_BRONZE:
        return TIER_BRONZE
    if current_count < TIER_SILVER:
        return TIER_SILVER
    if current_count < TIER_GOLD:
        return TIER_GOLD
    return None  # Already at max tier


def get_user_limit(user_id: int) -> int:
    """How many products to return for this user (based on tier)."""
    stats = get_user_stats(user_id)
    if not stats:
        return 3  # default for unknown users
    tier = stats["tier"]
    return {
        "standard": 3,
        "bronze": 4,
        "silver": 5,
        "gold": 7,
    }.get(tier, 3)


def get_leaderboard(limit: int = 10) -> list[dict]:
    """Top referrers (for showing on /leaderboard or for analytics)."""
    with _conn() as cur:
        rows = cur.execute(
            "SELECT first_name, referral_count, tier FROM users "
            "WHERE referral_count > 0 "
            "ORDER BY referral_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"first_name": r[0] or "Anonymous", "count": r[1], "tier": r[2]}
        for r in rows
    ]


# Auto-initialize on import
init_referrals_db()
