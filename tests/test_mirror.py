# ~/calendar_bot/tests/test_mirror.py
import pytest
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from utils import mirror
from utils.mirror import (
    ensure_mirror, reconcile_mirrors, is_self_organized, _snapshot, _mirror_body,
    apply_instance_exception, SHARED_CALENDAR_ID,
)


class _Resp:
    def __init__(self, status):
        self.status = status
        self.reason = "error"


def _http_error(status):
    return HttpError(_Resp(status), b'{}')


@pytest.fixture
def event():
    return {
        'id': 'evt1',
        'summary': 'Invited Meeting',
        'organizer': {'email': 'boss@example.com', 'self': False},
        'start': {'dateTime': '2030-09-05T10:00:00Z'},
        'end': {'dateTime': '2030-09-05T11:00:00Z'},
        'location': 'Room A',
    }


# --- is_self_organized ---

def test_self_organized_true_when_self():
    assert is_self_organized({'organizer': {'self': True}}) is True

def test_self_organized_false_when_not_self():
    assert is_self_organized({'organizer': {'self': False}}) is False

def test_self_organized_true_when_organizer_absent():
    # Missing organizer info -> keep existing invite behavior, don't mirror.
    assert is_self_organized({}) is True


# --- ensure_mirror ---

def test_ensure_mirror_creates_new(event):
    service = MagicMock()
    service.events().insert().execute.return_value = {'id': 'mirror1'}
    with patch.object(mirror, 'load_mirror_map', return_value={}), \
         patch.object(mirror, 'save_mirror_map') as save:
        assert ensure_mirror(service, 'joeltimm@gmail.com', event) is True
    # Inserted onto the shared calendar and persisted the mapping.
    insert_kwargs = service.events().insert.call_args.kwargs
    assert insert_kwargs['calendarId'] == SHARED_CALENDAR_ID
    saved_map = save.call_args.args[0]
    assert saved_map['joeltimm@gmail.com::evt1']['mirror_id'] == 'mirror1'


def test_ensure_mirror_skips_when_unchanged(event):
    service = MagicMock()
    existing = {'joeltimm@gmail.com::evt1': {'mirror_id': 'mirror1', 'snapshot': _snapshot(event)}}
    with patch.object(mirror, 'load_mirror_map', return_value=existing), \
         patch.object(mirror, 'save_mirror_map') as save:
        assert ensure_mirror(service, 'joeltimm@gmail.com', event) is True
    service.events().insert.assert_not_called()
    service.events().patch.assert_not_called()
    save.assert_not_called()


def test_ensure_mirror_patches_when_changed(event):
    service = MagicMock()
    stale = {'joeltimm@gmail.com::evt1': {'mirror_id': 'mirror1', 'snapshot': {'summary': 'old'}}}
    with patch.object(mirror, 'load_mirror_map', return_value=stale), \
         patch.object(mirror, 'save_mirror_map'):
        ensure_mirror(service, 'joeltimm@gmail.com', event)
    patch_kwargs = service.events().patch.call_args.kwargs
    assert patch_kwargs['calendarId'] == SHARED_CALENDAR_ID
    assert patch_kwargs['eventId'] == 'mirror1'


def test_ensure_mirror_skips_gracefully_without_access(event):
    service = MagicMock()
    service.events().insert().execute.side_effect = _http_error(403)
    with patch.object(mirror, 'load_mirror_map', return_value={}), \
         patch.object(mirror, 'save_mirror_map') as save:
        assert ensure_mirror(service, 'joeltimm@gmail.com', event) is False
    save.assert_not_called()


# --- reconcile_mirrors ---

def test_reconcile_deletes_mirror_when_source_cancelled(event):
    service = MagicMock()
    service.events().get().execute.return_value = {'id': 'evt1', 'status': 'cancelled'}
    mirror_map = {'joeltimm@gmail.com::evt1': {'mirror_id': 'mirror1', 'snapshot': {}}}
    with patch.object(mirror, 'load_mirror_map', return_value=mirror_map), \
         patch.object(mirror, 'save_mirror_map') as save:
        reconcile_mirrors(lambda cal: service)
    service.events().delete.assert_called_once()
    # Mapping entry removed.
    assert save.call_args.args[0] == {}


def test_reconcile_deletes_mirror_when_source_gone(event):
    service = MagicMock()
    service.events().get().execute.side_effect = _http_error(404)
    mirror_map = {'joeltimm@gmail.com::evt1': {'mirror_id': 'mirror1', 'snapshot': {}}}
    with patch.object(mirror, 'load_mirror_map', return_value=mirror_map), \
         patch.object(mirror, 'save_mirror_map') as save:
        reconcile_mirrors(lambda cal: service)
    service.events().delete.assert_called_once()
    assert save.call_args.args[0] == {}


def test_reconcile_patches_mirror_when_source_moved(event):
    service = MagicMock()
    service.events().get().execute.return_value = event  # current source state
    stale = {'joeltimm@gmail.com::evt1': {'mirror_id': 'mirror1', 'snapshot': {'summary': 'old time'}}}
    with patch.object(mirror, 'load_mirror_map', return_value=stale), \
         patch.object(mirror, 'save_mirror_map'):
        reconcile_mirrors(lambda cal: service)
    service.events().patch.assert_called_once()


# --- recurrence + instance exceptions ---

def test_mirror_body_copies_recurrence():
    ev = {'summary': 'Weekly', 'start': {}, 'end': {}, 'recurrence': ['RRULE:FREQ=WEEKLY']}
    assert _mirror_body(ev)['recurrence'] == ['RRULE:FREQ=WEEKLY']


def _exception(status=None):
    e = {
        'id': 'master1_20300101', 'recurringEventId': 'master1',
        'originalStartTime': {'dateTime': '2030-01-01T09:00:00Z'},
        'start': {'dateTime': '2030-01-01T15:00:00Z'}, 'end': {'dateTime': '2030-01-01T16:00:00Z'},
        'summary': 'Moved occurrence',
    }
    if status:
        e['status'] = status
    return e


def test_apply_instance_exception_cancels_mirror_instance():
    service = MagicMock()
    service.events().instances().execute.return_value = {'items': [{'id': 'mir1_i', 'status': 'confirmed'}]}
    mm = {'cal@x.com::master1': {'mirror_id': 'mir1', 'snapshot': {}}}
    with patch.object(mirror, 'load_mirror_map', return_value=mm):
        apply_instance_exception(service, 'cal@x.com', _exception(status='cancelled'))
    service.events().delete.assert_called_once()
    service.events().patch.assert_not_called()


def test_apply_instance_exception_moves_mirror_instance():
    service = MagicMock()
    service.events().instances().execute.return_value = {'items': [{'id': 'mir1_i', 'status': 'confirmed'}]}
    mm = {'cal@x.com::master1': {'mirror_id': 'mir1', 'snapshot': {}}}
    with patch.object(mirror, 'load_mirror_map', return_value=mm):
        apply_instance_exception(service, 'cal@x.com', _exception())
    service.events().patch.assert_called_once()
    service.events().delete.assert_not_called()


def test_apply_instance_exception_noop_when_series_not_mirrored():
    service = MagicMock()
    with patch.object(mirror, 'load_mirror_map', return_value={}):
        apply_instance_exception(service, 'cal@x.com', _exception(status='cancelled'))
    service.events().delete.assert_not_called()
    service.events().patch.assert_not_called()


# --- series-aware pruning (#recurring mirrors were pruned on first poll) ---

def _reconcile(source_event, mirror_map):
    service = MagicMock()
    service.events().get().execute.return_value = source_event
    with patch.object(mirror, 'load_mirror_map', return_value=mirror_map), \
         patch.object(mirror, 'save_mirror_map') as save:
        reconcile_mirrors(lambda cal: service)
    return service, save


def test_end_dt_open_ended_series_is_none():
    ev = {'end': {'dateTime': '2020-01-01T11:00:00Z'}, 'recurrence': ['RRULE:FREQ=WEEKLY;BYDAY=SA']}
    assert mirror._end_dt(ev) is None


def test_end_dt_bounded_series_uses_until():
    ev = {'end': {'date': '2020-01-02'}, 'recurrence': ['RRULE:FREQ=WEEKLY;UNTIL=20261014;BYDAY=TH']}
    assert mirror._end_dt(ev).date().isoformat() == '2026-10-15'  # UNTIL + 1 day pad


def test_end_dt_count_series_is_none():
    ev = {'end': {'date': '2020-01-02'}, 'recurrence': ['RRULE:FREQ=WEEKLY;COUNT=5']}
    assert mirror._end_dt(ev) is None


def test_reconcile_keeps_open_ended_series_whose_first_occurrence_is_past():
    # First occurrence long past, but the series is still running: must stay tracked.
    src = {
        'id': 'evt1', 'status': 'confirmed', 'summary': 'Weekly',
        'organizer': {'email': 'boss@example.com', 'self': False},
        'start': {'dateTime': '2020-01-01T10:00:00Z'}, 'end': {'dateTime': '2020-01-01T11:00:00Z'},
        'recurrence': ['RRULE:FREQ=WEEKLY'],
    }
    snap = _snapshot(src)
    _, save = _reconcile(src, {'joeltimm@gmail.com::evt1': {'mirror_id': 'm1', 'snapshot': snap}})
    save.assert_not_called()  # nothing pruned, nothing changed


def test_reconcile_prunes_single_event_long_past():
    src = {
        'id': 'evt1', 'status': 'confirmed', 'summary': 'Old',
        'organizer': {'email': 'boss@example.com', 'self': False},
        'start': {'dateTime': '2020-01-01T10:00:00Z'}, 'end': {'dateTime': '2020-01-01T11:00:00Z'},
    }
    service, save = _reconcile(src, {'joeltimm@gmail.com::evt1': {'mirror_id': 'm1', 'snapshot': _snapshot(src)}})
    service.events().delete.assert_not_called()  # mirror kept as history
    assert save.call_args.args[0] == {}


# --- needs_mirror (no duplicate for events covered by a native invite) ---

def test_needs_mirror_true_for_external_organizer(event):
    assert mirror.needs_mirror(event) is True


def test_needs_mirror_false_when_organizer_is_a_source_calendar(event):
    ev = dict(event, organizer={'email': 'tsouthworth@gmail.com', 'self': False})
    assert mirror.needs_mirror(ev) is False


def test_needs_mirror_false_when_shared_calendar_already_invited(event):
    ev = dict(event, attendees=[{'email': SHARED_CALENDAR_ID, 'responseStatus': 'needsAction'}])
    assert mirror.needs_mirror(ev) is False


def test_reconcile_removes_mirror_when_source_now_covered_by_invite(event):
    src = dict(event, status='confirmed', organizer={'email': 'tsouthworth@gmail.com', 'self': False})
    service, save = _reconcile(src, {'joeltimm@gmail.com::evt1': {'mirror_id': 'm1', 'snapshot': _snapshot(src)}})
    service.events().delete.assert_called_once()
    assert save.call_args.args[0] == {}
