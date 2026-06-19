# ~/calendar_bot/tests/test_clones.py
from unittest.mock import MagicMock, patch

from utils import clones
from utils.clones import record_clone, remove_clone


def test_record_clone_persists_mapping():
    with patch.object(clones, 'load_clone_map', return_value={}), \
         patch.object(clones, 'save_clone_map') as save:
        record_clone('cal@x.com', 'src1', 'clone1')
    saved = save.call_args.args[0]
    assert saved['cal@x.com::src1']['clone_id'] == 'clone1'


def test_remove_clone_deletes_and_forgets():
    service = MagicMock()
    cmap = {'cal@x.com::src1': {'clone_id': 'clone1'}}
    with patch.object(clones, 'load_clone_map', return_value=cmap), \
         patch.object(clones, 'save_clone_map') as save:
        remove_clone(service, 'cal@x.com', 'src1')
    del_kwargs = service.events().delete.call_args.kwargs
    assert del_kwargs['calendarId'] == 'cal@x.com'
    assert del_kwargs['eventId'] == 'clone1'
    assert save.call_args.args[0] == {}  # mapping entry removed


def test_remove_clone_noop_when_untracked():
    service = MagicMock()
    with patch.object(clones, 'load_clone_map', return_value={}), \
         patch.object(clones, 'save_clone_map') as save:
        remove_clone(service, 'cal@x.com', 'src1')
    service.events().delete.assert_not_called()
    save.assert_not_called()
