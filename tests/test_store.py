import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store

@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path)
    area = store.add_area('Desk', [0, 0, 1, 1], 'Books allowed', b'png fixture')
    yield store, area
    store.close()

def scan(store, area, status='clutter_present', mode='live', threshold=30, now=100, generation=0):
    return store.observe(area, status, 'Visible objects', generation, mode, threshold, now)

def test_thirty_valid_observations_with_invalid_gaps(setup):
    store, area = setup
    for i in range(29):
        assert not scan(store, area, now=i)
        assert not scan(store, area, 'unable_to_assess', now=i+.5)
    assert store.areas()[0]['count'] == 29
    assert scan(store, area)
    assert not scan(store, area)
    assert store.areas()[0]['alerted']

def test_tidy_resets_and_next_episode_alerts(setup):
    store, area = setup
    assert scan(store, area, threshold=1)
    scan(store, area, 'tidy')
    assert store.areas()[0]['count'] == 0
    assert not store.areas()[0]['alerted']
    assert scan(store, area, threshold=1)

def test_modes_do_not_share_counters(setup):
    store, area = setup
    assert scan(store, area, mode='demo', threshold=1)
    assert store.areas()[0]['count'] == 0
    assert not store.areas()[0]['alerted']
    assert store.areas('demo')[0]['count'] == 1

def test_snooze_delays_without_repeated_alert(setup):
    store, area = setup
    store.snooze(area, 60, now=100)
    assert not scan(store, area, threshold=1, now=120)
    assert not scan(store, area, 'unable_to_assess', threshold=1, now=170)
    assert scan(store, area, threshold=1, now=171)
    store.snooze(area, 60, now=180)
    assert not scan(store, area, threshold=1, now=250)

def test_reset_rejects_stale_results(setup):
    store, area = setup
    scan(store, area)
    store.reset_area(area)
    assert not scan(store, area, threshold=1)
    assert not store.history()[0]['status'] == 'tidy'
    assert store.areas()[0]['count'] == 0
    assert scan(store, area, generation=1, threshold=1)

def test_reference_and_preferences_reset(setup):
    store, area = setup
    scan(store, area)
    store.update_reference(area, b'new png')
    assert store.areas()[0]['generation'] == 1
    assert Path(store.areas()[0]['reference']).read_bytes() == b'new png'
    store.update_preferences(area, 'No dishes')
    assert store.areas()[0]['generation'] == 2
    assert store.areas()[0]['count'] == 0

def test_restart_persists_settings_counts_and_alert(tmp_path):
    store = Store(tmp_path)
    area = store.add_area('Desk', [0,0,1,1], '', b'png')
    store.set_setting('monitoring', False)
    assert scan(store, area, threshold=1)
    store.close()
    store = Store(tmp_path)
    assert store.get_setting('monitoring') is False
    assert store.areas()[0]['count'] == 1
    assert not scan(store, area, threshold=1)
    store.close()

def test_metadata_bounded_and_delete_owned_only(setup):
    store, area = setup
    unrelated = store.data_dir / 'keep.txt'
    unrelated.write_text('private unrelated data')
    for i in range(510):
        scan(store, area, 'unable_to_assess', now=i)
    assert len(store.history()) == 500
    reference = Path(store.areas()[0]['reference'])
    store.delete_data()
    assert not reference.exists()
    assert store.areas() == []
    assert store.history() == []
    assert unrelated.exists()
    assert not scan(store, area, threshold=1)

@pytest.mark.parametrize('status,threshold', [('bad',1), ('tidy',0), ('tidy',True), ('tidy',1.5)])
def test_invalid_observations_rejected(setup,status,threshold):
    store, area = setup
    with pytest.raises(ValueError):
        scan(store, area, status, threshold=threshold)
    assert not store.history()

@pytest.mark.parametrize('rect', [[-1,0,1,1], [0,0,0,1], [0,0,2,1], [float('nan'),0,1,1]])
def test_invalid_rectangles_rejected(setup,rect):
    store, _ = setup
    with pytest.raises(ValueError):
        store.add_area('Bad', rect, '', b'png')

def test_cleaned_resets_only_selected_mode_and_rejects_pending(setup):
    store, area = setup
    assert scan(store, area, mode='live', threshold=1)
    assert scan(store, area, mode='demo', threshold=1)
    store.reset_episode(area, 'demo')
    assert store.areas('demo')[0]['count'] == 0
    assert not store.areas('demo')[0]['alerted']
    assert store.areas('live')[0]['count'] == 1
    assert store.areas('live')[0]['alerted']
    assert not scan(store, area, mode='demo', generation=0, threshold=1)
    assert not scan(store, area, mode='live', generation=0, threshold=1)
    assert scan(store, area, mode='demo', generation=1, threshold=1)
    assert not scan(store, area, mode='live', generation=1, threshold=1)


def test_reset_episode_validates_mode(setup):
    store, area = setup
    with pytest.raises(ValueError):
        store.reset_episode(area, 'bad')

def test_delete_removes_owned_orphans_preserves_other_files(setup):
    store, area = setup
    orphan_png = store.references / ('a' * 32 + '.png')
    orphan_tmp = store.references / ('b' * 32 + '.tmp')
    unrelated_png = store.references / 'family.png'
    unrelated_tmp = store.references / 'notes.tmp'
    for path in (orphan_png, orphan_tmp, unrelated_png, unrelated_tmp):
        path.write_bytes(b'fixture')
    store.delete_data()
    assert not orphan_png.exists()
    assert not orphan_tmp.exists()
    assert unrelated_png.exists()
    assert unrelated_tmp.exists()
    assert store.areas() == []


def test_delete_failure_reopens_database_and_surfaces_error(setup, monkeypatch):
    store, area = setup
    reference = Path(store.areas()[0]['reference'])
    real_unlink = Path.unlink
    def fail_owned_reference(path, *args, **kwargs):
        if path == reference:
            raise PermissionError('Reference is locked')
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', fail_owned_reference)
    with pytest.raises(PermissionError, match='locked'):
        store.delete_data()
    assert store.areas()[0]['id'] == area
    store.set_setting('still_usable', True)
    assert store.get_setting('still_usable') is True
    assert reference.exists()
