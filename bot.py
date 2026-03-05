import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import random
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import pytz

# ─── CONFIG ───────────────────────────────────────────────
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
QUIZ_HOUR = 1   # 1 AM
QUIZ_MINUTE = 0
TIMEZONE = "Africa/Cairo"  # Egypt timezone

# ─── TOPICS ───────────────────────────────────────────────
TOPICS = {
    "DSA": "Data Structures & Algorithms (time/space complexity, Big-O notation, sorting, searching, trees, graphs, dynamic programming)",
    "Databases": "Databases (SQL, indexing, query optimization, normalization, transactions, ACID properties, NoSQL vs SQL)",
    "Machine Learning": "Machine Learning algorithms (regression, classification, clustering, overfitting, bias-variance tradeoff, evaluation metrics, feature engineering)",
    "Deep Learning": "Deep Learning & Neural Networks (backpropagation, CNNs, RNNs, transformers, attention mechanism, activation functions, training tricks)"
}

# ─── BOT SETUP ────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store the current question context per channel
current_quiz = {}

# ─── GROQ API CALL ────────────────────────────────────────
async def ask_groq(prompt: str, system: str = "") -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"].strip()

# ─── GENERATE QUESTION ────────────────────────────────────
async def generate_question(topic_key: str) -> str:
    topic_desc = TOPICS[topic_key]
    prompt = f"""Generate ONE challenging but fair quiz question about: {topic_desc}

Rules:
- Test deep understanding, not just memorization
- Can be conceptual, analytical, or scenario-based
- Keep it to 1-3 sentences max
- Do NOT include the answer
- Output the raw question only, no prefixes"""

    return await ask_groq(prompt)

# ─── GRADE ANSWER ─────────────────────────────────────────
async def grade_answer(question: str, topic: str, answer: str) -> str:
    prompt = f"""You are a strict but encouraging technical instructor.

Question: "{question}"
Topic: {topic}
Student's answer: "{answer}"

Respond in this exact format:

SCORE: [Excellent / Good / Partial / Needs Work]

FEEDBACK:
[2-3 sentences of specific feedback on what they got right and wrong]

OPTIMAL ANSWER:
[The ideal complete answer a senior engineer would give]

KEY INSIGHT:
[One memorable non-obvious insight they should internalize]"""

    return await ask_groq(prompt)

# ─── FETCH NEWS ───────────────────────────────────────────
async def fetch_news() -> str:
    today = datetime.now().strftime("%B %d, %Y")
    prompt = f"""You are an AI news curator. Today is {today}.

Generate a daily digest of the most important AI developments. Cover model releases, research, tools, and industry news.

Format as exactly 5 items:

[CATEGORY] Title
Summary in 2 sentences.

---

Use categories: MODEL, RESEARCH, TOOL, INDUSTRY, POLICY
Be specific with names and technical details."""

    return await ask_groq(prompt)

# ─── SEND QUIZ ────────────────────────────────────────────
async def send_daily_quiz():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    topic_key = random.choice(list(TOPICS.keys()))
    question = await generate_question(topic_key)

    current_quiz[CHANNEL_ID] = {
        "topic": topic_key,
        "question": question,
        "waiting_for_answer": True
    }

    embed = discord.Embed(
        title=f"🧠 Daily Quiz — {topic_key}",
        description=question,
        color=0xe8ff47
    )
    embed.set_footer(text="Reply with your answer and I'll grade it!")
    embed.timestamp = datetime.now()

    await channel.send(embed=embed)

# ─── SCHEDULED TASK ───────────────────────────────────────
@tasks.loop(minutes=1)
async def daily_quiz_task():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if now.hour == QUIZ_HOUR and now.minute == QUIZ_MINUTE:
        await send_daily_quiz()

# ─── BOT EVENTS ───────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Brain OS bot is online as {bot.user}")
    daily_quiz_task.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    # Check if we're waiting for a quiz answer in this channel
    if message.channel.id in current_quiz:
        quiz = current_quiz[message.channel.id]
        if quiz.get("waiting_for_answer") and not message.content.startswith("!"):
            quiz["waiting_for_answer"] = False

            # Show typing indicator
            async with message.channel.typing():
                grading = await grade_answer(
                    quiz["question"],
                    quiz["topic"],
                    message.content
                )

            # Parse score
            score = "Good"
            if "SCORE:" in grading:
                score_line = grading.split("SCORE:")[1].split("\n")[0].strip()
                score = score_line

            score_colors = {
                "Excellent": 0xe8ff47,
                "Good": 0x47d4ff,
                "Partial": 0xff9f47,
                "Needs Work": 0xff6b47
            }
            color = score_colors.get(score, 0x47d4ff)

            embed = discord.Embed(
                title=f"📊 Score: {score}",
                description=grading.replace(f"SCORE: {score}", "").strip(),
                color=color
            )
            embed.set_footer(text="Use !quiz for a new question anytime")
            await message.channel.send(embed=embed)

# ─── COMMANDS ─────────────────────────────────────────────
@bot.command(name="quiz")
async def quiz_command(ctx, topic: str = None):
    """Trigger a quiz manually. Usage: !quiz or !quiz DSA"""
    if topic and topic not in TOPICS:
        await ctx.send(f"❌ Unknown topic. Choose from: {', '.join(TOPICS.keys())}")
        return

    topic_key = topic if topic else random.choice(list(TOPICS.keys()))

    async with ctx.typing():
        question = await generate_question(topic_key)

    current_quiz[ctx.channel.id] = {
        "topic": topic_key,
        "question": question,
        "waiting_for_answer": True
    }

    embed = discord.Embed(
        title=f"🧠 Quiz — {topic_key}",
        description=question,
        color=0xe8ff47
    )
    embed.set_footer(text="Reply with your answer and I'll grade it!")
    await ctx.send(embed=embed)


@bot.command(name="news")
async def news_command(ctx):
    """Get today's AI news digest."""
    msg = await ctx.send("📡 Fetching today's AI digest...")

    async with ctx.typing():
        news = await fetch_news()

    items = news.split("---")
    embed = discord.Embed(
        title="📰 Daily AI Digest",
        color=0x47d4ff,
        timestamp=datetime.now()
    )

    cat_emojis = {
        "MODEL": "🤖", "RESEARCH": "🔬",
        "TOOL": "🛠️", "INDUSTRY": "💼", "POLICY": "⚖️"
    }

    for item in items:
        item = item.strip()
        if not item:
            continue
        lines = item.split("\n")
        if not lines:
            continue
        title_line = lines[0].strip()
        summary = " ".join(lines[1:]).strip()

        import re
        cat_match = re.search(r'\[([A-Z]+)\]', title_line)
        cat = cat_match.group(1) if cat_match else "NEWS"
        emoji = cat_emojis.get(cat, "📌")
        title = re.sub(r'\[[A-Z]+\]\s*', '', title_line).strip()

        embed.add_field(
            name=f"{emoji} {title}",
            value=summary or "—",
            inline=False
        )

    await msg.delete()
    await ctx.send(embed=embed)


@bot.command(name="topics")
async def topics_command(ctx):
    """List available quiz topics."""
    embed = discord.Embed(title="📚 Available Topics", color=0xe8ff47)
    for key, desc in TOPICS.items():
        embed.add_field(name=f"`!quiz {key}`", value=desc[:80] + "...", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="help_brainos")
async def help_command(ctx):
    """Show all commands."""
    embed = discord.Embed(title="🧠 Brain OS — Commands", color=0xe8ff47)
    embed.add_field(name="!quiz", value="Random quiz question", inline=False)
    embed.add_field(name="!quiz DSA", value="Quiz on a specific topic (DSA, Databases, Machine Learning, Deep Learning)", inline=False)
    embed.add_field(name="!news", value="Get today's AI news digest", inline=False)
    embed.add_field(name="!topics", value="List all available topics", inline=False)
    embed.set_footer(text="Daily quiz fires automatically at 1:00 AM Cairo time")
    await ctx.send(embed=embed)


# ─── RUN ──────────────────────────────────────────────────
bot.run(DISCORD_TOKEN)
