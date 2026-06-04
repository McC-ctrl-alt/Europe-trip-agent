# telegram_bot.py
# Phase 3 wired to Telegram

import anthropic
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from Europe_Itinerary_Agent_P1 import run_phase1_agent
from Europe_Itinerary_Agent_P2 import run_phase2_agent

# ── CONFIG ──────────────────────────────────────────────────────
import os
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ITINERARY_PATH = "itinerary.md"
ACTION_LIST_PATH = "action_list.md"

# ── LOAD FILES ──────────────────────────────────────────────────
def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ── ANTHROPIC CLIENT ─────────────────────────────────────────────
client = anthropic.Anthropic()

# Store conversation history per user
conversation_histories = {}

# ── MESSAGE HANDLER ──────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    itinerary = read_file(ITINERARY_PATH)
    action_list = read_file(ACTION_LIST_PATH)

    # ── SYSTEM PROMPT ───────────────────────────────────────────────
    today = datetime.now().strftime("%A, %B %d, %Y")
    system_prompt = f"""
You are a personal travel assistant for Liam, a 20-year-old Canadian
backpacker on a 9-week solo trip through Europe. Budget ~$7,730 CAD.

TODAY'S DATE: {today}

CURRENT ROUTE (updated):
London → Paris → Amsterdam → Florence → Pisa → Prague → Budapest → Zagreb → Split → Korcula → Dubrovnik → Albania → Greece → Istanbul → Bangkok

FULL ITINERARY:
{itinerary}

ACTION LIST:
{action_list}

INSTRUCTIONS:
- Liam is on his phone while travelling — keep responses under 5 sentences unless providng a city primer
- Be direct — give addresses, times, prices
- For emergencies give immediate practical alternatives
- Flag urgent bookings when relevant

CITY PRIMERS:
When asked for a primer on any city, respond in this exact format:

**[City Name]** — [one sentence that captures the city's essence]

📜 HISTORY: 2-3 sentences. Focus on what shaped the city's character, not a Wikipedia timeline.
🧭 CONTEXT: 2-3 sentences. What to notice and appreciate that most travellers walk past.
💡 TIPS: 3 bullet points. Practical, specific to solo budget travellers.
⚡ DO THIS: One single best experience for someone who values depth over tourism.

Keep the entire primer under 200 words.
"""

    user_id = update.effective_user.id
    user_message = update.message.text

    print(f"Message from {user_id}: {user_message}")

    # Get or create conversation history for this user
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []

    # Add user message to history
    conversation_histories[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Keep history to last 10 messages to manage tokens
    if len(conversation_histories[user_id]) > 10:
        conversation_histories[user_id] = conversation_histories[user_id][-10:]

    # Call Claude
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,
        messages=conversation_histories[user_id]
    )

    reply = response.content[0].text

    # Add reply to history
    conversation_histories[user_id].append({
        "role": "assistant",
        "content": reply
    })

    # Send reply back to Telegram
    await update.message.reply_text(reply)

# ── REFRESH HANDLER ──────────────────────────────────────────────
async def handle_refresh(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Refreshing itinerary from Excel and Gmail...")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, run_phase1_agent)
        await update.message.reply_text("Phase 1 done. Rebuilding action list...")
        await loop.run_in_executor(None, run_phase2_agent)
        await update.message.reply_text("Done! Itinerary and action list updated.")
    except Exception as e:
        await update.message.reply_text(f"Refresh failed: {e}")

# ── RUN BOT ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Travel bot starting...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("refresh", handle_refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running! Message it on Telegram.")
    app.run_polling(drop_pending_updates=True)