# 🧠 Brain OS — Discord Bot

A personal learning bot that quizzes you daily and delivers AI news digests.

## Commands
| Command | Description |
|---|---|
| `!quiz` | Random quiz question |
| `!quiz DSA` | Quiz on specific topic |
| `!quiz Databases` | Quiz on Databases |
| `!quiz Machine Learning` | Quiz on ML |
| `!quiz Deep Learning` | Quiz on Deep Learning |
| `!news` | Today's AI news digest |
| `!topics` | List all topics |
| `!help_brainos` | Show all commands |

Daily quiz fires automatically at **1:00 AM Cairo time**.

---

## Deploy on Railway (Free)

1. Go to **railway.app** and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Upload this folder to a GitHub repo first (see below)
4. Railway will auto-detect and deploy it

### Upload to GitHub
1. Go to **github.com** → New repository → name it `brain-os-bot` → Create
2. Upload all 3 files: `bot.py`, `requirements.txt`, `railway.toml`
3. Connect repo to Railway → Deploy

---

## Files
- `bot.py` — main bot code
- `requirements.txt` — Python dependencies  
- `railway.toml` — Railway deployment config
