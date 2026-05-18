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

itinerary = read_file(ITINERARY_PATH)
action_list = read_file(ACTION_LIST_PATH)

# ── SYSTEM PROMPT ───────────────────────────────────────────────
system_prompt = f"""
You are a personal travel assistant for Liam, a 20-year-old Canadian 
backpacker on a 9-week solo trip through Europe. Budget ~$7,200 CAD.
Route: London → Paris → Brussels → Amsterdam → Berlin → Prague → Vienna → Rome.

FULL ITINERARY:
{itinerary}

ACTION LIST:
{action_list}

INSTRUCTIONS:
- Liam is messaging you on his phone while travelling
- Keep ALL responses under 5 sentences — he's on the go
- Be direct and specific — give addresses, prices, times
- If asked about food, give 2-3 options with price range
- If something is cancelled or goes wrong, give immediate alternatives
- Always flag anything URGENT he needs to book
"""

# ── ANTHROPIC CLIENT ─────────────────────────────────────────────
client = anthropic.Anthropic()

# Store conversation history per user
conversation_histories = {}

# ── MESSAGE HANDLER ──────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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