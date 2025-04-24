from flask import Flask, request, Response
from process_event import handle_event, load_processed, save_processed

print("Starting Flask app...")

app = Flask(__name__)

try:
    processed_ids = load_processed()
    print("Loaded processed event IDs.")
except Exception as e:
    print(f"Error loading processed events: {e}")
    processed_ids = set()

@app.route('/webhook', methods=['POST'])
def webhook():
    print("📩 Webhook received!")

    try:
        print("📦 Importing Google API client...")
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        print("🔑 Loading credentials...")
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        print("🔧 Building calendar service...")
        service = build('calendar', 'v3', credentials=creds)

        print("📅 Fetching recent events...")
        events_result = service.events().list(
            calendarId='primary',
            maxResults=5,
            orderBy='startTime',
            singleEvents=True
        ).execute()

        events = events_result.get('items', [])
        print(f"📆 Found {len(events)} events.")

        for event in events:
            eid = event['id']
            summary = event.get('summary', 'No title')
            print(f"👉 Event: {eid} - {summary}")

            if eid not in processed_ids:
                print(f"✅ New event found: {eid}")
                handle_event(eid)
                processed_ids.add(eid)
            else:
                print(f"⏩ Already processed: {eid}")

        save_processed(processed_ids)
        print("💾 Saved processed event IDs.")

    except Exception as e:
        print(f"❌ ERROR in webhook: {e}")

    return Response("OK", status=200)

if __name__ == "__main__":
    print("Running app.run()...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
