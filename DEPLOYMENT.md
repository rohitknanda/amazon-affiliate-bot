# 🚀 Deployment Guide — Run Your Bot 24/7

Your bot currently only runs when your laptop is on. To make money while you sleep, you need to deploy it to a server that runs 24/7. Here are the 3 best options ranked by ease.

---

## 🏆 Option 1: Railway.app (RECOMMENDED — Easiest, Free)

**Cost:** Free $5 credit per month (enough for this bot to run 24/7 forever)
**Time:** ~10 minutes
**Difficulty:** ⭐ Easy

### Step-by-step:

**1. Push your code to GitHub** (skip if you already use GitHub)

```bash
# In your bot folder:
cd amazon-affiliate-bot
git init
git add .
git commit -m "Initial commit"
```

Then go to https://github.com → click "New repository" → name it `amazon-affiliate-bot` → **make it PRIVATE** (important — your code has logic you don't want public) → create.

Copy the commands GitHub shows you (looks like this):
```bash
git remote add origin https://github.com/YOUR-USERNAME/amazon-affiliate-bot.git
git branch -M main
git push -u origin main
```

⚠️ **VERY IMPORTANT:** Make sure `.gitignore` is in your folder before pushing. It prevents your `.env` file (with your secret keys) from going to GitHub. Verify with:
```bash
cat .gitignore
```

**2. Deploy on Railway**

- Go to https://railway.app → Sign up with GitHub (free)
- Click **"New Project"** → **"Deploy from GitHub repo"**
- Authorize Railway to access your repo → select `amazon-affiliate-bot`
- Railway auto-detects Python and starts building 🎉

**3. Add your environment variables**

After deploy starts:
- Click your project → **Variables** tab → **+ New Variable**
- Add each one (paste the actual values from your local `.env`):

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | (your bot token from @BotFather) |
| `ANTHROPIC_API_KEY` | (your sk-ant-... key) |
| `AMAZON_AFFILIATE_TAG` | (your tag like `yourname-21`) |
| `AMAZON_COUNTRY` | `IN` |

- Click **"Deploy"** again to restart with new vars

**4. Verify it's running**

- Click **"Deployments"** tab → click latest deployment → **"View Logs"**
- You should see: `🤖 Bot is running. Press Ctrl+C to stop.`
- Open Telegram → message your bot → it should reply!

**Done!** Your bot now runs 24/7. Every push to GitHub auto-redeploys.

---

## 💪 Option 2: VPS (Most Reliable, $5-7/month)

**Cost:** ₹400-600/month
**Time:** ~20 minutes
**Difficulty:** ⭐⭐ Moderate
**Best for:** scaling to many users, full control

### Recommended providers (India-friendly):
- **DigitalOcean** ($6/mo) — has Bangalore region, accepts UPI via partner
- **Hetzner Cloud** (€4/mo ≈ ₹360) — cheapest, EU-based but works for India
- **Contabo** ($5/mo) — cheap but slower
- **Vultr** ($6/mo) — has Mumbai region

### Step-by-step (DigitalOcean example):

**1. Create a server**
- Sign up at digitalocean.com → "Create Droplet"
- Choose: **Ubuntu 24.04**, **Basic plan**, **$6/month**, **Bangalore region**
- SSH keys recommended (or use password)
- Click create — wait 60 seconds

**2. Connect to your server**
```bash
ssh root@YOUR_SERVER_IP
```

**3. Install Python and Git**
```bash
apt update && apt install -y python3-pip python3-venv git
```

**4. Clone your code**
```bash
git clone https://github.com/YOUR-USERNAME/amazon-affiliate-bot.git
cd amazon-affiliate-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**5. Create .env on the server**
```bash
nano .env
```
Paste your env vars (Ctrl+O to save, Ctrl+X to exit).

**6. Run as a background service** (so it survives reboots and SSH disconnects)

Create a systemd service:
```bash
nano /etc/systemd/system/affiliatebot.service
```

Paste this (change the paths if needed):
```ini
[Unit]
Description=Amazon Affiliate Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/amazon-affiliate-bot
Environment="PATH=/root/amazon-affiliate-bot/venv/bin"
ExecStart=/root/amazon-affiliate-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and enable:
```bash
systemctl daemon-reload
systemctl enable affiliatebot
systemctl start affiliatebot
systemctl status affiliatebot   # check it's running
```

**View live logs:**
```bash
journalctl -u affiliatebot -f
```

**To update after code changes:**
```bash
cd ~/amazon-affiliate-bot
git pull
systemctl restart affiliatebot
```

---

## 🎓 Option 3: Replit (Free, browser-based, easiest learning)

**Cost:** Free (basic) — but bot sleeps if free tier; needs $10/mo "Reserved VM" for true 24/7
**Time:** 5 minutes
**Difficulty:** ⭐ Very easy

### Step-by-step:

1. Go to https://replit.com → Sign up
2. **Create Repl** → **"Import from GitHub"** → paste your repo URL
3. Once imported, click **🔒 Secrets** in left sidebar → add all your env vars
4. Click **"Run"** at top → bot starts!
5. To keep it running 24/7: upgrade to **"Reserved VM"** ($10/mo) — without this, the free tier sleeps after inactivity

**Note:** Replit's free tier is fine for testing but sleeps. Use Railway free instead for 24/7.

---

## 📊 Which option should you pick?

| If you... | Pick |
|---|---|
| Are a beginner, want it free and easy | **Railway** ✅ |
| Want maximum reliability and plan to scale | **VPS (DigitalOcean)** |
| Want to learn in your browser | **Replit** |

**My recommendation:** Start with **Railway** today (free, 10 minutes). Move to a VPS later when you have 100+ daily users and want full control.

---

## 🆘 Common deployment issues

**Bot deploys but doesn't respond to messages?**
- Check logs — usually means env vars are missing/wrong
- Verify your Telegram token is exact (no extra spaces)

**"Module not found" error?**
- Make sure `requirements.txt` is in your repo root

**Railway shows "build failed"?**
- Check the build log — usually a Python version issue
- Add a `runtime.txt` file with content `python-3.12` to force Python version

**Bot runs but suddenly stops after a few hours?**
- On Railway free tier: you're using compute credits → check usage in dashboard
- On Replit free: it sleeps without Reserved VM
- On VPS: check `journalctl -u affiliatebot` for crash logs

**Multiple instances responding at once?**
- You probably have the bot running locally AND on the server. Stop the local one — only ONE instance can poll Telegram at a time.

---

## 💡 Pro tips after deployment

1. **Set up a webhook for stats** — every Monday, get a Telegram message with your weekly stats (queries, clicks). I can build this if you want.

2. **Monitor with UptimeRobot (free)** — pings your bot every 5 minutes, emails you if it goes down.

3. **Use Cloudflare Workers as a "wake-up" service** — if you're on a free tier that sleeps, ping it every few minutes to keep it awake.

4. **Backup your analytics DB weekly** — the SQLite file has your user data. Copy it to your computer occasionally.

Happy deploying! 🚀
