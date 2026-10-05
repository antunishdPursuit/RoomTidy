import os,sys,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest,numpy as np
from PySide6.QtWidgets import QApplication,QMessageBox
import app as module
from vision import encode_png

@pytest.fixture
def window(tmp_path,monkeypatch):
    application=QApplication.instance() or QApplication([])
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    w=module.Window()
    yield w
    w.close()

def add(w):
    f=np.full((100,100,3),120,np.uint8);f[10:40]=220
    aid=w.store.add_area('desk',[0,0,1,1],'books allowed',encode_png(f))
    w.store.set_setting('source_'+aid,[0,[100,100],'camera'])
    w.refresh();w.areas.setCurrentRow(0)
    return aid,f

def test_preview_invalidates_pending(window,monkeypatch):
    monkeypatch.setattr(window,"preview_capture",lambda:None)
    window.pending=window.epoch;window.enabled=True
    epoch=window.epoch
    window.toggle_preview()
    assert window.epoch>epoch and window.pending is None and not window.enabled

def test_cleaned_demo_preserves_live(window):
    aid,_=add(window)
    window.store.observe(aid,'clutter_present','cup',0,'live',30)
    window.mode.setCurrentIndex(1)
    window.areas.setCurrentRow(0)
    window.cleaned()
    assert window.store.areas('live')[0]['count']==1

def test_hourly_gate_and_stale_result(window):
    aid,f=add(window);a=window.store.areas()[0]
    result=(f,[(a,{'status':'clutter_present','evidence':'cup'})],'live',time.time())
    window.completed(('analysis',result,None,window.epoch))
    window.completed(('analysis',result,None,window.epoch))
    assert window.store.areas()[0]['count']==1
    window.store.reset_episode(aid,'live')
    window.completed(('analysis',result,None,window.epoch))
    assert window.store.areas()[0]['count']==0

def test_preferences_loaded_and_saved(window,monkeypatch):
    aid,_=add(window)
    assert window.preferences.text()=='books allowed'
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    window.preferences.setText('dishes removed');window.save_preferences()
    assert window.store.areas()[0]['preferences']=='dishes removed'

def test_reference_requires_fresh_source(window):
    _,f=add(window);window.preview.display(f)
    with pytest.raises(ValueError):window.reference_ready()
    window.frame_kind='camera';window.frame_time=time.monotonic();window.previewing=True
    window.reference_ready()

def test_delete_clears_pending(window,monkeypatch):
    add(window);window.pending=window.epoch
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    window.delete_data()
    assert not window.store.areas() and window.pending is None and not window.enabled


def test_tidy_not_hourly_limited(window):
    aid,f=add(window);a=window.store.areas()[0];now=time.time()
    window.completed(('analysis',(f,[(a,{'status':'clutter_present','evidence':'cup'})],'live',now),None,window.epoch))
    window.completed(('analysis',(f,[(a,{'status':'tidy','evidence':'clear'})],'live',now+10),None,window.epoch))
    assert window.store.areas()[0]['count']==0

def test_camera_change_clears_reference_eligibility(window):
    _,f=add(window);window.preview.display(f);window.frame_kind='camera';window.frame_time=time.monotonic()
    window.camera.setValue(1)
    assert window.preview.frame is None and window.frame_kind is None


def test_saved_reference_is_validated_snapshot(window,monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    _,frame=add(window)
    window.preview.display(frame);window.preview.rect=[0,0,1,1]
    window.frame_kind='camera';window.frame_time=time.monotonic();window.previewing=True
    expected=encode_png(frame)
    def change_frame(*args):
        window.preview.frame=np.zeros_like(frame)
        return 'snapshot',True
    monkeypatch.setattr(QInputDialog,'getText',change_frame)
    window.add_area()
    area=window.store.areas()[-1]
    assert area['name']=='snapshot'
    assert Path(area['reference']).read_bytes()==expected

def test_snooze_visible(window):
    aid,_=add(window)
    window.store.observe(aid,'clutter_present','cup',0,'live',1)
    window.snooze()
    assert 'Snoozed until' in window.areas.item(0).text()
