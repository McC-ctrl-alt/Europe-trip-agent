# phase2_agent.py
# Reads itinerary.md and produces a prioritised action list

import anthropic

ITINERARY_PATH = "itinerary.md"
OUTPUT_PATH = "action_list.md"

def read_itinerary(path):
    with open(path, "r") as f:
        return f.read()

def run_phase2_agent():
    client = anthropic.Anthropic()

    print("📋 Reading itinerary...")
    itinerary = read_itinerary(ITINERARY_PATH)

    prompt = f"""
You are a expert travel research agent for a 20-year-old Canadian backpacker 
on a 9-week solo trip through Europe on a shoestring budget (~$7,200 CAD total).

ACCURACY RULES:
- For booking links, only use these verified base URLs:
    * Eurostar: eurostar.com
    * Flixbus: flixbus.com  
    * Hostelworld: hostelworld.com
    * Tower of London: hrp.org.uk
    * Churchill War Rooms: iwm.org.uk
    * Westminster Abbey: westminster-abbey.org
    * Versailles: chateauversailles.fr
    * Pompeii: pompeiisites.org
    * Keukenhof: keukenhof.nl
- NEVER invent a specific URL path — only provide the homepage
- For prices, always add ⚠️ VERIFY PRICE — may have changed
- For opening times, always add ⚠️ CHECK BEFORE VISITING
- Flag anything time-sensitive with 🔴

CURRENT ITINERARY:
{itinerary}

CITIES IN ORDER: London → Paris → Brussels → Amsterdam → Berlin → Pruage → Vienna → Rome
TRAVEL STYLE: Shoestring, hostels, free experiences prioritised, selective paid ones

YOUR TASK:
Go through the itinerary day by day and produce a prioritised action list of 
everything that should be booked or researched in advance.

For each item include:
- CITY
- WHAT needs booking
- WHY it needs advance booking
- URGENCY: 🔴 URGENT (book today) / 🟡 SOON (within a week) / 🟢 FLEXIBLE
- ESTIMATED COST in CAD
- BOOKING LINK where possible

Categories to check:
1. Transport (Eurostar, Flixbus, flights)
2. Accommodation (hostels not yet booked)
3. Experiences (museum tickets, tours that sell out)
4. Restaurants (any that require reservations)
5. Day trips (optional) (Versailles, Pompeii, Keukenhof, Hamburg, Koln, Strasbourg) - focus on maximizing the city since I have limited days per city.

End with a GAPS section flagging anything missing from the itinerary entirely.
"""

    print("🤖 Claude is researching your action list...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    action_list = message.content[0].text

    print("💾 Saving action list...")
    with open(OUTPUT_PATH, "w") as f:
        f.write(action_list)

    print(f"\n✅ Done! Action list saved to {OUTPUT_PATH}")
    print("\n--- PREVIEW ---\n")
    print(action_list[:1000] + "...")

if __name__ == "__main__":
    run_phase2_agent()