# ~/calendar_bot/utils/clones.py
"""
Track events the bot clones so they can be cleaned up when their source is gone.

`birthday` events can't carry attendees, so the bot clones them onto the source
calendar (with the shared calendar invited). Those clones are independent events
with no link back to the original, so if the original birthday is removed the
clone would be orphaned. We record source -> clone here and delete the clone when
the source is cancelled/deleted.

(fromGmail events are intentionally deleted by the bot after duplication, so they
are deliberately not tracked here — tracking them would delete the duplicate.)
"""
import json
import os
from pathlib import Path

from googleapiclient.errors import HttpError

from utils.logger import logger

CLONE_FILE = Path(os.getenv('CLONE_FILE', 'data/cloned_events.json'))


def _key(source_calendar_id, event_id):
    return f"{source_calendar_id}::{event_id}"


def load_clone_map():
    if CLONE_FILE.exists():
        try:
            return json.loads(CLONE_FILE.read_text())
        except json.JSONDecodeError:
            logger.error("🧬 Clone map file is corrupt; starting fresh.")
    return {}


def save_clone_map(clone_map):
    CLONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLONE_FILE.write_text(json.dumps(clone_map, indent=2))


def record_clone(source_calendar_id, source_event_id, clone_id):
    """Remember that `source_event_id` was cloned into `clone_id`."""
    clone_map = load_clone_map()
    clone_map[_key(source_calendar_id, source_event_id)] = {'clone_id': clone_id}
    save_clone_map(clone_map)


def remove_clone(service, source_calendar_id, source_event_id):
    """Delete the clone for a now cancelled/deleted source event (no-op if none).

    The clone lives on the source calendar, so it is deleted with the source
    account's own service.
    """
    clone_map = load_clone_map()
    key = _key(source_calendar_id, source_event_id)
    record = clone_map.get(key)
    if not record:
        return
    clone_id = record.get('clone_id')
    if clone_id:
        try:
            service.events().delete(calendarId=source_calendar_id, eventId=clone_id).execute()
            logger.info("🗑️ Deleted an orphaned birthday clone whose source was removed.")
        except HttpError as e:
            if e.resp.status not in (404, 410):  # already gone is fine
                logger.error(f"Failed to delete clone {clone_id}: {e}")
    del clone_map[key]
    save_clone_map(clone_map)
