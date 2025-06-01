# register_webhook.py
from encrypted_env_loader import load_encrypted_env
load_encrypted_env()
import sys, os
import uuid
import msal
 
from utils.google_utils import build_calendar_service
from googleapiclient.discovery import build
from pathlib import Path
from common.credentials import load_credentials
#temporarily commented out for dockerization
##WEBHOOK_URL = os.getenv("WEBHOOK_URL") #localtunnel url
##SOURCE_CALENDARS = [c.strip() for c in os.getenv("SOURCE_CALENDARS", "").split(",") if c]

#if not WEBHOOK_URL:
 #   raise ValueError("❌ WEBHOOK_URL is not set in the .env file.")

#if not SOURCE_CALENDARS:
#    raise ValueError("❌ SOURCE_CALENDARS is not set or empty in the .env file.")

#for calendar_id in SOURCE_CALENDARS:
#    print(f"📡 Registering webhook for {calendar_id}...")

#    try:
#        service = build_calendar_service(calendar_id)
#        watch_request = {
#            'id': str(uuid.uuid4()),
#            'type': 'web_hook',
#            'address': WEBHOOK_URL,
#            'params': {
#                'ttl': '3600'  # 1 hour TTL
#            }
#        }

#        response = service.events().watch(calendarId='primary', body=watch_request).execute()
#        print(f"✅ Webhook registered for {calendar_id}")
#        print(f"🔗 Resource ID: {response.get('resourceId')}")
#        print(f"📆 Expiration: {response.get('expiration')}")

#    except Exception as e:
#        print(f"❌ Failed to register webhook for {calendar_id}: {e}")
