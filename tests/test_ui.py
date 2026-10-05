import os,sys,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from PySide6.QtWidgets import QMessageBox
from test_app import window,add
from vision import encode_png
import ui

def test_navigation_stops_hidden_preview(window,monkeypatch):
    window.reduce_motion.setChecked(True)
    ui.navigate(window,1);window.previewing=True;window.pending=window.epoch
    epoch=window.epoch
    ui.navigate(window,0)
    assert not window.previewing and window.pending is None and window.epoch>epoch

def test_guide_and_empty_setup(window):
    assert window.pages.count()==4
    assert not window.monitor.isEnabled()
    ui.navigate(window,3)
    assert window.pages.currentIndex()==3

def test_reduce_motion_persists(window):
    window.reduce_motion.setChecked(True);ui.navigate(window,2)
    assert window._page_animation is None and window.store.get_setting('reduce_motion') is True

def test_card_cleaned_applies_to_its_area(window):
    aid,_=add(window);window.store.observe(aid,'clutter_present','cup',0,'live',30)
    ui.area_action(window,aid,'cleaned')
    assert window.store.areas()[0]['count']==0

def test_footer_bounded(window):
    message='desk: visible items '*100
    window.status.setText(message)
    assert len(window.status.text())<260
    assert window.status.toolTip()==message

def test_updated_reference_thumbnail(window,monkeypatch):
    aid,frame=add(window)
    old=window.reference_view.pixmap().toImage()
    frame=frame.copy();frame[0:10]=200
    window.preview.display(frame);window.previewing=True;window.frame_kind='camera';window.frame_time=time.monotonic()
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    window.update_reference()
    assert window.reference_view.pixmap().toImage()!=old

def test_narrow_pages_without_horizontal_scroll(window):
    window.reduce_motion.setChecked(True);window.resize(740,500);window.show()
    from PySide6.QtWidgets import QApplication
    for index in range(4):
        ui.navigate(window,index);QApplication.processEvents()
        assert window.pages.currentWidget().horizontalScrollBar().maximum()==0


def test_card_actions_preserve_unsaved_preferences(window):
    aid,_=add(window)
    window.preferences.setText('new area draft')
    ui.area_action(window,aid,'snooze')
    assert window.preferences.text()=='new area draft'
    ui.area_action(window,aid,'cleaned')
    assert window.preferences.text()=='new area draft'

def test_untrusted_label_is_plain_text(window):
    from PySide6.QtCore import Qt
    text='<b>desk</b>'
    assert ui.label(text).textFormat()==Qt.PlainText
    window.status.setText(text)
    assert window.status.textFormat()==Qt.PlainText and window.status.text()==text

def test_check_button_disabled_during_notice(window):
    add(window);window.scan()
    assert window.pending is not None and not window.check_button.isEnabled()

def test_delete_resets_motion_and_placeholders(window,monkeypatch):
    window.reduce_motion.setChecked(True)
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    window.delete_data()
    assert not window.reduce_motion.isChecked()
    assert 'Open preview' in window.preview.text()
