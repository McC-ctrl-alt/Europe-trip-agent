# telegram_bot.py
# Phase 3 wired to Telegram

import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

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


# ── SYSTEM PROMPT ───────────────────────────────────────────────
system_prompt = f"""
You are a personal travel assistant for Liam, a 20-year-old Canadian 
backpacker on a 9-week solo trip through Europe. Budget ~$7,730 CAD.

CURRENT ROUTE (updated):
London → Paris → Amsterdam → Florence → Pisa → Prague → Vienna → Budapest → Istanbul → Bangkok

CURRENT STATUS:
- Currently on train Zurich → Milan → Florence
- Arriving Florence May 24
- Pisa May 27-31
- Prague → Vienna → Budapest → Istanbul → fly Bangkok ~June 30 - July 1st
- Meeting family Bangkok July 2 - 3, islands Jun 28-Jul 9

FULL ITINERARY:
{itinerary}

ACTION LIST:
{action_list}

INSTRUCTIONS:
- Liam is on his phone while travelling — keep responses under 5 sentences
- Be direct — give addresses, times, prices
- For emergencies give immediate practical alternatives
- Flag urgent bookings when relevant
"""
# ── ANTHROPIC CLIENT ─────────────────────────────────────────────
client = anthropic.Anthropic()

# Store conversation history per user
conversation_histories = {}

# ── MESSAGE HANDLER ──────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Taking the next two lines from the top to refresh every message
    itinerary = read_file(ITINERARY_PATH)
    action_list = read_file(ACTION_LIST_PATH)

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

# ── RUN BOT ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Travel bot starting...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running! Message it on Telegram.")
    app.run_polling()