# phase3_agent.py  
# Day-of assistant — knows your full itinerary, answers questions

import anthropic

ITINERARY_PATH = "itinerary.md"
ACTION_LIST_PATH = "action_list.md"

def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def run_phase3_assistant():
    client = anthropic.Anthropic()

    print("📖 Loading your itinerary...")
    itinerary = read_file(ITINERARY_PATH)
    action_list = read_file(ACTION_LIST_PATH)

    system_prompt = f"""
You are a personal travel assistant for Liam, a 20-year-old Canadian backpacker 
on a 9-week solo trip through Europe. You know his full itinerary and can answer 
any question about it instantly.

FULL ITINERARY:
{itinerary}

ACTION LIST:
{action_list}

KEY FACTS:
- Budget: ~$7,200 CAD total
- Payment: Wise card (tap anywhere)
- Style: Shoestring, loves free experiences, selective paid ones
- Route: London → Paris → Brussels → Amsterdam → Berlin → Pruage → Vienna → Rome
- Currently in London, checking out May 14

INSTRUCTIONS:
- Answer questions directly and concisely — Liam is on his phone on the go
- Always give practical next steps
- Flag urgent booking reminders when relevant
- If asked about alternatives (cancelled restaurant, missed train etc) 
  give 2-3 specific options with addresses
- Keep responses short — 3-5 sentences max unless asked for more. Do not use filer words where applicable - stay concise and specific.
"""

    print("\n🎒 Travel assistant ready! Ask me anything.")
    print("(type 'quit' to exit)\n")

    conversation_history = []

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Safe travels Liam! 🌍")
            break

        if not user_input:
            continue

        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=system_prompt,
            messages=conversation_history
        )

        assistant_reply = response.content[0].text

        conversation_history.append({
            "role": "assistant", 
            "content": assistant_reply
        })

        print(f"\nAssistant: {assistant_reply}\n")

if __name__ == "__main__":
    run_phase3_assistant()