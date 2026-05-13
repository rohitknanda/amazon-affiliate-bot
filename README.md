# 🛍️ Amazon Affiliate Telegram Bot

A complete AI-powered Telegram bot that recommends Amazon products with your affiliate links. Built with Claude AI for smart understanding of user queries.

## ✨ What this bot does

- Listens to messages on Telegram
- Uses Claude AI to understand what users want (e.g. *"wireless mouse under 1000"* → category: mouse, budget: ₹1000)
- Searches Amazon and returns 3 best products with **your affiliate links**
- Tracks queries and clicks in a local database for analytics
- Works in **two modes**: full Amazon API (real data) or instant fallback (no API approval needed)

## 🚀 Quick Start (15 minutes)

### Step 1 — Get your credentials

You need 3 things. Get them in any order:

**1. Telegram Bot Token (free, 2 minutes)**
- Open Telegram → search `@BotFather`
- Send `/newbot` → follow prompts → copy the token you get
- Save it as `TELEGRAM_BOT_TOKEN`

**2. Anthropic API Key (free $5 credit)**
- Go to https://console.anthropic.com
- Sign up → API Keys → Create Key → copy it
- Save it as `ANTHROPIC_API_KEY`
- Cost: ~₹0.10 per user query using Haiku 4.5 (very cheap)

**3. Amazon Affiliate Tag**
- You already have this since you have an Amazon affiliate account
- It looks like `yourname-21` (for Amazon India)
- Save it as `AMAZON_AFFILIATE_TAG`

### Step 2 — Install

```bash
# Clone or download these files into a folder, then:
cd amazon-affiliate-bot
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Configure

```bash
cp .env.example .env
# Now open .env in a text editor and fill in your 3 keys
```

### Step 4 — Run!

```bash
python bot.py
```

You'll see `🤖 Bot is running.` Open Telegram, find your bot, send any message like *"wireless mouse under 1500"* and watch the magic happen!

---

## 📊 How it works internally

```
User: "wireless mouse under 1500"
   ↓
[Telegram] receives message → forwards to bot.py
   ↓
[recommender.py] calls Claude AI to parse:
   { search_keywords: "wireless mouse",
     max_price: 1500,
     category: "wireless mouse" }
   ↓
[amazon.py] searches Amazon and builds product list
   ↓
[bot.py] sends 3 product cards with affiliate links
   ↓
User clicks → goes to Amazon → buys → you earn commission 💰
```

## 🔄 Two operating modes

### Mode 1: Fallback Mode (DEFAULT — works immediately)
- **No API approval needed** — works as soon as you start
- Generates Amazon search URLs with your affiliate tag baked in
- User clicks → lands on Amazon search results → any product they buy = your commission
- Perfect for getting started before Amazon approves PA-API access

### Mode 2: PA-API Mode (after Amazon approves you)
- Activated automatically when you fill in `AMAZON_ACCESS_KEY` + `AMAZON_SECRET_KEY` in `.env`
- Returns real product titles, prices, images, ratings
- Requires Amazon Associates approval (need 3 qualifying sales first)
- After approval: uncomment `python-amazon-paapi` in `requirements.txt` and install

---

## 🌍 Switching to other markets

In `.env`, change `AMAZON_COUNTRY`:
- `IN` → Amazon India 🇮🇳
- `US` → Amazon US 🇺🇸
- `UK` → Amazon UK 🇬🇧
- `DE` → Germany, `CA` → Canada, `AU` → Australia, `JP` → Japan

---

## 📈 Growing your bot (earning more)

### How to get users
1. **WhatsApp/Telegram groups** — share your bot link in deal-finder groups
2. **Reddit** — answer "what should I buy" questions, link to your bot
3. **Instagram bio** — "Need product recs? Chat with my AI bot →"
4. **YouTube** — make a video reviewing your bot, link in description
5. **Quora** — answer product questions, mention your bot

### Track your stats
```python
# In a separate terminal:
python -c "from analytics import get_stats; import json; print(json.dumps(get_stats(), indent=2))"
```

Shows: total queries, unique users, top searches, click rate.

---

## 🚢 Deploying 24/7 (so the bot works while you sleep)

### Option A: Free — Railway.app
1. Push code to GitHub
2. Sign up at railway.app → New Project → Deploy from GitHub
3. Add your env vars in Railway dashboard
4. Done — bot runs 24/7 free for 500 hours/month

### Option B: Cheap — DigitalOcean/Hetzner ($5/month)
```bash
# On your server:
git clone <your-repo>
cd amazon-affiliate-bot
pip install -r requirements.txt
# Create .env with your keys

# Run with systemd or screen:
screen -S bot
python bot.py
# Press Ctrl+A then D to detach — bot keeps running
```

### Option C: Free forever — Replit
1. Create new Repl → import from GitHub
2. Add env vars in Secrets tab
3. Run

---

## 💬 Moving to WhatsApp later

The bot logic in `bot.py` is platform-agnostic. To switch to WhatsApp:

1. Sign up for **Twilio WhatsApp API** or **Meta WhatsApp Business API**
2. Replace the Telegram handlers in `bot.py` with WhatsApp webhook handlers
3. The `recommender.py` and `amazon.py` files stay exactly the same

For an easier no-code WhatsApp route: use **Wati.io** or **Interakt** — they let you connect Claude API via webhooks without writing WhatsApp-specific code.

---

## 📁 Project structure

```
amazon-affiliate-bot/
├── bot.py                # Main Telegram bot (entry point)
├── recommender.py        # Claude AI query understanding
├── amazon.py             # Amazon product search (PA-API + fallback)
├── analytics.py          # SQLite query/click logging
├── config.py             # Environment variables
├── requirements.txt      # Python dependencies
├── .env.example          # Config template (copy to .env)
└── README.md             # This file
```

## 🐛 Troubleshooting

**Bot doesn't respond after I send a message?**
- Check the terminal for error messages
- Make sure all 3 required env vars are filled in `.env`

**"TELEGRAM_BOT_TOKEN not set" error?**
- You forgot to copy `.env.example` to `.env` and fill it in

**Claude API error?**
- Verify your API key starts with `sk-ant-`
- Make sure you have credits in your Anthropic account

**No products showing up?**
- In fallback mode, you should always get 3 search-link results
- Check the logs for error messages

---

## 💰 Cost breakdown

Per 1,000 user queries:
- Claude Haiku 4.5: ~₹50 (very cheap — handles 1000s of users on $5 free credit)
- Telegram: FREE
- Hosting on Railway: FREE up to 500 hrs/month
- **Total: ~₹50 to handle 1000 queries**

If even 1% of users buy something on Amazon and you average ₹100 commission, that's ₹1000 earned per ₹50 spent on AI. **20x ROI.**

---

## 📝 License

MIT — do whatever you want with this code.

Happy earning! 🚀
