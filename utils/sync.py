# ~/calendar_bot/utils/sync.py
"""
Incremental calendar sync using Google Calendar syncTokens.

Replaces the old "list the next 100 future events and dedupe by ID" poll with
proper incremental sync. Each calendar keeps a syncToken, so subsequent syncs
return only created / updated / deleted events — no 100-event cap, and updates
and deletions are delivered (not just first-seen creates).

The first sync for a calendar (or after a 410 token expiry) is a full sync
bounded by timeMin=now; it yields a fresh syncToken for incremental syncs after.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.errors import HttpError

from utils.logger import logger

SYNC_TOKEN_FILE = Path(os.getenv('SYNC_TOKEN_FILE', 'data/sync_tokens.json'))
_PAGE_SIZE = 2500  # max allowed; keeps the full initial sync to a few pages
# Bump whenever the list() query parameters change: a syncToken is only valid
# for the exact query that produced it, so a change must force a full resync.
# v2: switched from singleEvents=True (per-instance) to series-level sync.
_SYNC_VERSION = 2


def load_sync_tokens():
    if SYNC_TOKEN_FILE.exists():
        try:
            data = json.loads(SYNC_TOKEN_FILE.read_text())
            if isinstance(data, dict) and data.get('_version') == _SYNC_VERSION:
                return data.get('tokens', {})
            logger.info("🔄 Sync token version changed; ignoring old tokens (one full resync).")
        except json.JSONDecodeError:
            logger.error("🔄 Sync token file is corrupt; starting fresh (full resync).")
    return {}


def save_sync_tokens(tokens):
    SYNC_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_TOKEN_FILE.write_text(json.dumps({'_version': _SYNC_VERSION, 'tokens': tokens}, indent=2))


def _list_all(service, base_params):
    """Page through events().list, returning (events, next_sync_token).

    nextSyncToken only appears on the final page, so we carry it forward.
    """
    events = []
    sync_token = None
    page_token = None
    while True:
        params = dict(base_params)
        if page_token:
            params['pageToken'] = page_token
        resp = service.events().list(**params).execute()
        events.extend(resp.get('items', []))
        sync_token = resp.get('nextSyncToken') or sync_token
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return events, sync_token


def list_changes(service, calendar_id, stored_token):
    """Return (events, new_sync_token, is_full_sync).

    With a valid stored_token: an incremental sync returning only changed
    events (including cancelled ones, since showDeleted=True). Without a token,
    or on a 410 (expired token): a full sync bounded by timeMin=now.
    """
    common = dict(
        calendarId=calendar_id,
        singleEvents=False,  # series-level: recurring events as masters, not per-instance
        showDeleted=True,    # so deletions/cancellations are delivered incrementally
        maxResults=_PAGE_SIZE,
    )
    if stored_token:
        try:
            events, token = _list_all(service, dict(common, syncToken=stored_token))
            return events, token, False
        except HttpError as e:
            if e.resp.status == 410:  # token expired -> fall back to full resync
                logger.warning(f"🔄 Sync token for {calendar_id} expired; doing a full resync.")
            else:
                raise

    now = datetime.now(timezone.utc).isoformat()
    events, token = _list_all(service, dict(common, timeMin=now))
    return events, token, True
