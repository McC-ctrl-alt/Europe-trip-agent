import os
import json
import anthropic
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import re

def clean_email_body(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<')
    return text.strip()

# ── CONFIG ──────────────────────────────────────────────────────────────────
SHEET_ID = "1WfIepnwhg_01nCf0rGMBuWcmn17m0QcD2ZbDIvpE7iw"   # paste the ID from your Google Sheet URL
OUTPUT_PATH = "itinerary.md"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

# ── AUTH ─────────────────────────────────────────────────────────────────────
def get_credentials():
    creds = None
    token_env = os.environ.get("GOOGLE_TOKEN_JSON")
    creds_env = os.environ.get("GOOGLE_CREDENTIALS_JSON")

    if token_env:
        creds = Credentials.from_authorized_user_info(json.loads(token_env), SCOPES)
    elif os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if not token_env:
            with open("token.json", "w") as f:
                f.write(creds.to_json())

    if not creds or not creds.valid:
        if creds_env:
            flow = InstalledAppFlow.from_client_config(json.loads(creds_env), SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return creds

# ── TOOL 1: Read Gmail confirmations ────────────────────────────────────────
def read_gmail_confirmations(creds):
    service = build("gmail", "v1", credentials=creds)

    search_queries = [
        "reservation confirmed after:2026/05/01",
        "St. Christopher's after:2026/05/01",
        "Porter Airlines after:2026/05/01",
        "Expedia after:2026/05/01",
        "Flixbus after:2026/05/01",
        "Eurostar after:2026/05/01",
        "easyJet after:2026/05/01",
        "Ryanair after:2026/05/01",
        "booking confirmed",
        "your itinerary",
        "e-ticket",
        "Porter Airlines",
        "Expedia booking",
        "Thai Airways",
        "Lomprayah",
        "Ko Samui",
        "Hostelworld"
    ]

    emails = []
    for query in search_queries:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=5
        ).execute()

        for msg in results.get("messages", []):
            email = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()

            payload = email["payload"]
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data", "")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8")
                            break
                    if "parts" in part:
                        for subpart in part["parts"]:
                            if subpart["mimeType"] == "text/plain":
                                data = subpart["body"].get("data", "")
                                if data:
                                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                                    break
            elif "body" in payload:
                data = payload["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8")

            body = clean_email_body(body)
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            emails.append({
                "subject": headers.get("Subject", "No subject"),
                "date": headers.get("Date", "Unknown date"),
                "body": body[:2000]
            })

    return emails

# ── TOOL 2: Read Google Sheet ────────────────────────────────────────────────
def read_google_sheet(creds, sheet_id):
    service = build("sheets", "v4", credentials=creds)
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

    sheets_data = {}
    for s in spreadsheet["sheets"]:
        sheet_name = s["properties"]["title"]
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_name
        ).execute()
        sheets_data[sheet_name] = result.get("values", [])

    return sheets_data

# ── TOOL 3: Save output file ─────────────────────────────────────────────────
def save_itinerary(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Saved to {path}"

# ── PHASE 1 AGENT ────────────────────────────────────────────────────────────
def run_phase1_agent():
    client = anthropic.Anthropic()

    print("🔑 Authenticating with Google...")
    creds = get_credentials()

    print("📧 Reading Gmail confirmations...")
    emails = read_gmail_confirmations(creds)

    print("📊 Reading Google Sheet tracker...")
    sheet_data = read_google_sheet(creds, SHEET_ID)

    prompt = f"""
You are a precise travel document parser. Your job is ONLY to extract
confirmed booking information from the emails and Google Sheet data provided.

STRICT RULES:
- ONLY report what is explicitly stated in the source data
- NEVER infer, assume, or fill gaps with logical guesses
- If a field is not clearly stated, write "NOT FOUND"
- If you are uncertain about any detail, flag it with ⚠️
- DO NOT add bookings that are not confirmed in the data
- ONLY include bookings relevant to this Europe trip
- IGNORE any bookings in Canada or pre-April 2026
- IGNORE restaurant reservations unless in Europe
- IGNORE any refunded or cancelled bookings

For each booking found, extract ONLY:
- Booking type (flight/hostel/transport)
- Confirmation number (exact, as written)
- Departure point (exact, as written)
- Arrival point (exact, as written)
- Date and time (exact, as written)
- Cost (exact, as written)
- Source email subject line
- Route: London → Paris → Amsterdam → Florence → Pisa → Prague → Budapest → Zagreb → Split → Korcula → Dubrovnik → Albania → Greece → Istanbul → Bangkok

EMAILS PROVIDED:
{json.dumps(emails, indent=2)}

GOOGLE SHEET DATA:
{json.dumps(sheet_data, indent=2)}

Flag any contradictions between sources with ⚠️ CONFLICT.
"""

    print("🤖 Claude is building your itinerary...")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    itinerary = message.content[0].text

    print("💾 Saving itinerary...")
    save_itinerary(itinerary, OUTPUT_PATH)

    print(f"\n✅ Done! Itinerary saved to {OUTPUT_PATH}")
    print("\n--- PREVIEW ---\n")
    print(itinerary[:1000] + "...")

    return itinerary

# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_phase1_agent()
