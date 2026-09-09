#!/usr/bin/env python3
"""
One-off cleanup of orphaned shared-calendar mirrors.

Before the series-aware prune fix, a mirror of a *recurring* source series was
dropped from the mirror map on the first poll after creation (Google reports a
master's `end` as the first occurrence's end, so it always looked "long past").
Every later edit of the series then inserted a fresh mirror, leaving stacks of
stale, untracked copies on the shared calendar that never received moves or
cancellations.

This script finds bot-created mirrors on the shared calendar that are not in
the mirror map and are either recurring or start in the future, and:

  * deletes them, then
  * if the source series still exists and still needs a mirror under the
    current rules (see utils.mirror.needs_mirror), re-mirrors it once so it is
    tracked again.

Past single-occurrence orphans are left alone: they were pruned by design as a
historical record.

Dry-run by default; pass --apply to make changes. Run inside the container (or
with GOOGLE_AUTH_PATH set) so the same tokens and data/ files are used:

    docker exec calendar_bot-calendar_bot-1 python scripts/cleanup_orphan_mirrors.py [--apply]
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.errors import HttpError  # noqa: E402

from utils.google_utils import build_calendar_service  # noqa: E402
from utils.mirror import (  # noqa: E402
    SHARED_CALENDAR_ID, SOURCE_CALENDARS, load_mirror_map, is_self_organized,
    needs_mirror, ensure_mirror,
)

MIRROR_MARKER = 'Mirrored by Calendar Bot'


def _start_val(event):
    st = event.get('start') or {}
    return st.get('dateTime') or st.get('date') or ''


def _start_dt(event):
    val = _start_val(event)
    try:
        if len(val) == 10:
            return datetime.fromisoformat(val).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    except ValueError:
        return None


def _list_all(service, **params):
    items, page = [], None
    while True:
        resp = service.events().list(**dict(params, pageToken=page) if page else params).execute()
        items.extend(resp.get('items', []))
        page = resp.get('nextPageToken')
        if not page:
            return items


def find_orphans(service, mirror_map):
    tracked = {rec.get('mirror_id') for rec in mirror_map.values()}
    now = datetime.now(timezone.utc)
    orphans = []
    for ev in _list_all(service, calendarId=SHARED_CALENDAR_ID, q=MIRROR_MARKER,
                        singleEvents=False, showDeleted=False, maxResults=2500):
        if ev.get('status') == 'cancelled' or ev.get('recurringEventId'):
            continue
        if not (ev.get('description') or '').startswith(MIRROR_MARKER):
            continue
        if ev['id'] in tracked:
            continue
        start = _start_dt(ev)
        if ev.get('recurrence') or (start and start > now):
            orphans.append(ev)
    return orphans


def find_source(services, orphan):
    """Locate the source event an orphan mirrors: same title + first start on a
    source calendar, not organized by that calendar's owner."""
    for cal, svc in services.items():
        try:
            candidates = _list_all(svc, calendarId=cal, q=orphan.get('summary', ''),
                                   singleEvents=False, showDeleted=False, maxResults=250)
        except HttpError as e:
            print(f"    ! could not search {cal}: {e}")
            continue
        for ev in candidates:
            if ev.get('recurringEventId') or ev.get('status') == 'cancelled':
                continue
            if ev.get('summary') != orphan.get('summary'):
                continue
            if _start_val(ev)[:10] != _start_val(orphan)[:10]:
                continue
            if is_self_organized(ev):
                continue
            return cal, svc, ev
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='delete orphans (and re-mirror where still needed)')
    args = ap.parse_args()

    services = {cal: build_calendar_service(cal) for cal in SOURCE_CALENDARS}
    shared_svc = next(iter(services.values()))
    mirror_map = load_mirror_map()

    orphans = find_orphans(shared_svc, mirror_map)
    print(f"{len(orphans)} orphaned mirror(s) on {SHARED_CALENDAR_ID} "
          f"({'APPLYING' if args.apply else 'dry run'}):\n")

    remirror = {}  # source key -> (cal, svc, event); de-duped across orphan stacks
    for ev in sorted(orphans, key=lambda e: (e.get('summary') or '', _start_val(e))):
        rec = ' [recurring]' if ev.get('recurrence') else ''
        print(f"  {ev['id']}  {_start_val(ev)[:16]}  {ev.get('summary')!r}{rec}")
        cal, svc, src = find_source(services, ev)
        if src is None:
            print("      source: not found on any source calendar -> delete only")
        elif not needs_mirror(src):
            print(f"      source: {cal}::{src['id']} is covered by a native invite -> delete only")
        else:
            print(f"      source: {cal}::{src['id']} still needs a mirror -> delete, then re-mirror once")
            remirror[f"{cal}::{src['id']}"] = (cal, svc, src)
        if args.apply:
            try:
                shared_svc.events().delete(calendarId=SHARED_CALENDAR_ID, eventId=ev['id']).execute()
                print("      deleted")
            except HttpError as e:
                if e.resp.status in (404, 410):
                    print("      already gone")
                else:
                    print(f"      ! delete failed: {e}")

    if remirror:
        print(f"\n{len(remirror)} series to re-mirror (tracked):")
        for key, (cal, svc, src) in remirror.items():
            print(f"  {key}  {src.get('summary')!r}")
            if args.apply:
                ok = ensure_mirror(svc, cal, src)
                print("      re-mirrored" if ok else "      ! re-mirror skipped (no write access?)")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to make these changes.")


if __name__ == '__main__':
    main()
