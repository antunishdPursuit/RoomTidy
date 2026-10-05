"""Workflow tests use a mock analyzer, not claims about model accuracy."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
import app
import photo_demo


@pytest.fixture
def demo(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    normal = tmp_path / 'ordinary'
    normal.mkdir()
    sentinel = normal / 'RoomTidy' / 'private.txt'
    sentinel.parent.mkdir()
    sentinel.write_text('preserve normal profile')
    monkeypatch.setenv('LOCALAPPDATA', str(normal))
    photos = tmp_path / 'photos'
    photos.mkdir()
    for filename in ('reference.png', 'clutter.png', 'blocked.png'):
        cv2.imwrite(str(photos / filename), np.full((64,96,3), 100, dtype=np.uint8))
    monkeypatch.setattr(photo_demo, 'PHOTOS', photos)
    class FakeAnalyzer:
        statuses = []
        def analyze(self, reference, current, preferences):
            return {'status': self.statuses.pop(0), 'evidence': 'Mock visible evidence'}
        def close(self): pass
    monkeypatch.setattr(app, 'Analyzer', FakeAnalyzer)
    monkeypatch.setattr(app.Camera, 'capture', lambda *args: pytest.fail('Photo walkthrough must not read a camera'))
    window = photo_demo.PhotoDemoWindow()
    notifications = []
    monkeypatch.setattr(window, 'notify', lambda name,mode: notifications.append((name,mode)))
    yield application, window, sentinel, notifications
    window.close()
    application.processEvents()


def await_result(application, window):
    deadline = time.monotonic() + 5
    while window.busy and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(.001)
    application.processEvents()
    assert not window.busy


def test_isolated_profile_and_no_automatic_camera(demo):
    application, window, sentinel, notifications = demo
    assert window.store.data_dir == sentinel.parents[1] / 'RoomTidyPhotoDemo' / 'RoomTidy'
    assert os.environ['LOCALAPPDATA'] == str(sentinel.parents[1])
    assert not window.timer.isActive()
    assert not window.preview_timer.isActive()
    assert not window.monitor.isEnabled()
    assert not window.check_button.isEnabled()
    assert not window.preview_button.isEnabled()
    assert window.mode_name() == 'demo'
    assert window.threshold.value() == 3
    assert not window.guide_next.isEnabled()
    for method in ('scan','toggle_preview','toggle_monitor','preview_capture','capture_pending','tick'):
        getattr(window, method)()
    assert sentinel.read_text() == 'preserve normal profile'


def test_seven_real_workflow_steps_with_mock_analyzer(demo):
    application, window, sentinel, notifications = demo
    window.start_walkthrough()
    window.analyzer.statuses = [step[2] for step in photo_demo.STEPS]
    for index, step in enumerate(photo_demo.STEPS):
        window.next_step()
        await_result(application, window)
        assert window.step_index == index + 1
        assert window.store.areas('demo')[0]['count'] == step[3]
        assert not window.monitor.isEnabled()
        assert not window.check_button.isEnabled()
    assert len(notifications) == 1
    assert notifications[0][1] == 'demo'
    assert window.store.areas('demo')[0]['count'] == 0
    assert not window.guide_next.isEnabled()
    assert len(window.store.history('demo')) == 7
    assert sentinel.read_text() == 'preserve normal profile'


def test_mismatch_keeps_actual_status_and_reset_requires_explicit_start(demo):
    application, window, sentinel, notifications = demo
    window.start_walkthrough()
    window.analyzer.statuses = ['clutter_present']
    window.next_step()
    await_result(application, window)
    assert window.store.areas('demo')[0]['count'] == 1
    assert 'Does not match' in window.guide_result.text()
    window.reset_walkthrough()
    assert window.store.areas('demo')[0]['count'] == 0
    assert not window.guide_next.isEnabled()
    assert len(window.store.history('demo')) == 1
    window.start_walkthrough()
    assert window.store.history('demo') == []
    assert sentinel.exists()


def test_missing_assets_do_not_delete_existing_demo_data(demo):
    application, window, sentinel, notifications = demo
    window.store.set_setting('keep', True)
    (photo_demo.PHOTOS / 'blocked.png').unlink()
    window.start_walkthrough()
    assert window.store.get_setting('keep') is True
    assert window.guide_area is None
    assert 'could not start' in window.status.toolTip()

def test_failed_restart_disables_next_and_discards_stale_area(demo, monkeypatch):
    application, window, sentinel, notifications = demo
    window.start_walkthrough()
    assert window.guide_area is not None
    assert window.guide_next.isEnabled()
    def fail_save(*args, **kwargs):
        raise OSError('Reference save failed')
    monkeypatch.setattr(window.store, 'add_area', fail_save)
    window.start_walkthrough()
    assert window.guide_area is None
    assert window.step_index == 0
    assert window.pending_step is None
    assert not window.guide_next.isEnabled()
    assert window.store.areas('demo') == []
    assert 'Reference save failed' in window.status.toolTip()
    assert sentinel.exists()


def test_missing_current_picture_has_explicit_thumbnail_message(demo):
    application, window, sentinel, notifications = demo
    window.show_current_photo(photo_demo.PHOTOS / 'missing.png')
    assert 'unavailable' in window.guide_current.text()
    window.start_walkthrough()
    assert window.guide_current.pixmap() is not None
    window.show_current_photo(photo_demo.PHOTOS / 'missing.png')
    window.reset_walkthrough()
    assert window.guide_current.pixmap() is not None
