# ~/calendar_bot/tests/test_sync.py
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError

from utils.sync import list_changes


class _Resp:
    def __init__(self, status):
        self.status = status
        self.reason = "error"


def _http_error(status):
    return HttpError(_Resp(status), b'{}')


def _service_returning(pages):
    """A mock Calendar service whose events().list().execute() yields `pages`
    in order (each page a dict, or an exception to raise)."""
    service = MagicMock()
    service.events().list().execute.side_effect = pages
    return service


def test_full_sync_when_no_token():
    service = _service_returning([{'items': [{'id': 'a'}, {'id': 'b'}], 'nextSyncToken': 'tok1'}])
    events, token, is_full = list_changes(service, 'cal@x.com', None)
    assert is_full is True
    assert [e['id'] for e in events] == ['a', 'b']
    assert token == 'tok1'
    # Full sync must be bounded by timeMin, not a syncToken.
    last_call = service.events().list.call_args.kwargs
    assert 'timeMin' in last_call and 'syncToken' not in last_call


def test_incremental_sync_with_token():
    service = _service_returning([{'items': [{'id': 'c'}], 'nextSyncToken': 'tok2'}])
    events, token, is_full = list_changes(service, 'cal@x.com', 'tok1')
    assert is_full is False
    assert [e['id'] for e in events] == ['c']
    assert token == 'tok2'
    assert service.events().list.call_args.kwargs.get('syncToken') == 'tok1'


def test_expired_token_falls_back_to_full_sync():
    # First (incremental) call 410s, then the full sync succeeds.
    service = _service_returning([_http_error(410), {'items': [{'id': 'd'}], 'nextSyncToken': 'tok3'}])
    events, token, is_full = list_changes(service, 'cal@x.com', 'stale')
    assert is_full is True
    assert [e['id'] for e in events] == ['d']
    assert token == 'tok3'


def test_pagination_collects_all_pages_and_final_token():
    service = _service_returning([
        {'items': [{'id': 'p1'}], 'nextPageToken': 'pg2'},
        {'items': [{'id': 'p2'}], 'nextSyncToken': 'tokfinal'},
    ])
    events, token, is_full = list_changes(service, 'cal@x.com', None)
    assert [e['id'] for e in events] == ['p1', 'p2']
    assert token == 'tokfinal'


def test_non_410_error_propagates():
    service = _service_returning([_http_error(500)])
    try:
        list_changes(service, 'cal@x.com', 'tok')
        assert False, "expected HttpError to propagate"
    except HttpError as e:
        assert e.resp.status == 500
