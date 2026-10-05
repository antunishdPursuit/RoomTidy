"""RoomTidy: local, explicit-reference room reminders."""
import sys, os, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRect
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication,QMainWindow,QLabel,QMessageBox,QInputDialog,QRubberBand
from store import Store
from vision import Camera, Analyzer, encode_png, crop, quality_reason

def guarded(fn):
    def wrapped(self,*args,**kwargs):
        try:return fn(self,*args,**kwargs)
        except Exception as exc:self.status.setText("Could not complete: "+str(exc))
    return wrapped

class Events(QObject):
    done = Signal(object)
    toast_error = Signal(str)

class Preview(QLabel):
    def __init__(self):
        super().__init__('Open camera preview, then drag to select an area.')
        self.setMinimumSize(640,360)
        self.setAlignment(Qt.AlignCenter)
        self.frame = None
        self.rect = None
        self.origin = None
        self.band=QRubberBand(QRubberBand.Rectangle,self)
        self.setObjectName('cameraPreview')
    def display(self,frame):
        self.frame=frame
        rgb=frame[:,:,::-1].copy()
        h,w,_=rgb.shape
        pix=QPixmap.fromImage(QImage(rgb.data,w,h,rgb.strides[0],QImage.Format_RGB888).copy())
        self.setPixmap(pix.scaled(self.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.frame is not None:
            self.display(self.frame)
            if self.rect and self.pixmap():
                p=self.pixmap();x,y,width,height=self.rect
                self.band.setGeometry(QRect(round((self.width()-p.width())/2+x*p.width()),round((self.height()-p.height())/2+y*p.height()),round(width*p.width()),round(height*p.height())))
    def mousePressEvent(self,e):
        if self.frame is not None:
            self.origin=e.position().toPoint(); self.band.setGeometry(QRect(self.origin,self.origin)); self.band.show()
    def mouseMoveEvent(self,e):
        if self.origin is not None:self.band.setGeometry(QRect(self.origin,e.position().toPoint()).normalized())
    def mouseReleaseEvent(self,e):
        if self.origin is None or self.pixmap() is None: return
        p=self.pixmap(); ox=(self.width()-p.width())/2; oy=(self.height()-p.height())/2
        r=QRect(self.origin,e.position().toPoint()).normalized()
        x=max(0,min(1,(r.x()-ox)/p.width())); y=max(0,min(1,(r.y()-oy)/p.height()))
        right=max(0,min(1,(r.right()-ox)/p.width())); bottom=max(0,min(1,(r.bottom()-oy)/p.height()))
        if right-x>.03 and bottom-y>.03:
            self.rect=[x,y,right-x,bottom-y]
            self.setToolTip('Selected area: '+str([round(v,2) for v in self.rect]))
        self.origin=None

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('RoomTidy - local room reminders')
        self.resize(1120,800)
        self.setMinimumSize(740,500)
        screen=QApplication.primaryScreen()
        if screen:
            available=screen.availableGeometry()
            self.resize(min(1120,max(740,available.width()-24)),min(800,max(500,available.height()-24)))
        self.store=Store(Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'RoomTidy')
        self.analyzer=Analyzer()
        self.pool=ThreadPoolExecutor(max_workers=1)
        self.events=Events(); self.events.done.connect(self.completed);self.events.toast_error.connect(lambda message:self.status.setText(message))
        self.busy=False; self.enabled=False; self.closing=False; self.close_requested=False; self.epoch=0
        self.previewing=False; self.pending=None; self.next_scan=0; self.frame_time=0; self.frame_kind=None
        import ui
        ui.build(self,Preview)
        self.refresh()
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(500)
        self.preview_timer=QTimer(self); self.preview_timer.timeout.connect(self.preview_capture); self.preview_timer.start(1000)
    def button(self,layout,text,fn):
        b=QPushButton(text); b.clicked.connect(lambda checked=False:fn()); layout.addWidget(b); return b
    def mode_name(self): return 'demo' if self.mode.currentIndex() else 'live'
    def selected(self):
        item=self.areas.currentItem()
        return item.data(Qt.UserRole) if item else None
    def refresh(self):
        selected=self.selected(); self.areas.blockSignals(True); self.areas.clear()
        for a in self.store.areas(self.mode_name()):
            from PySide6.QtWidgets import QListWidgetItem
            reminder=(" | Snoozed until "+time.strftime("%H:%M",time.localtime(a["snooze_until"]))) if a["snooze_until"]>time.time() else (" | Reminder active" if a["alerted"] else "")
            item=QListWidgetItem(f"{a['name']} - {a['count']}/{self.threshold.value()} valid clutter checks"+reminder)
            item.setData(Qt.UserRole,a['id']); self.areas.addItem(item)
            if a['id']==selected: self.areas.setCurrentItem(item)
        self.areas.blockSignals(False)
        import ui
        ui.render(self)
    def load_preferences(self,*args):
        area=next((a for a in self.store.areas(self.mode_name()) if a['id']==self.selected()),None)
        if area:
            self.preferences.setText(area['preferences'])
            self.reference_view.setPixmap(QPixmap(area['reference']).scaled(200,130,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        import ui
        ui.sync(self)
    def threshold_changed(self,n):
        self.store.set_setting("threshold",n);self.refresh()
    @guarded
    def save_preferences(self):
        if self.selected() is not None:
            if QMessageBox.question(self,'Shared baseline','Save preferences and reset BOTH live and demo tracking for this area?')==QMessageBox.Yes:
                self.store.update_preferences(self.selected(),self.preferences.text());self.store.set_setting('last_valid_'+self.selected(),0);self.refresh()
    def camera_changed(self,index):
        self.enabled=False;self.previewing=False;self.epoch+=1;self.pending=None
        self.preview.frame=None;self.preview.rect=None;self.frame_kind=None;self.frame_time=0;self.preview.clear();self.preview.band.hide()
        self.store.set_setting('camera',index);self.monitor.setText('Resume monitoring')
        self.status.setText('Camera changed. Existing references require explicit reconfiguration before monitoring.')
    def submit(self,fn,kind):
        if self.busy or self.closing or self.close_requested:return False
        self.busy=True; epoch=self.epoch
        import ui
        ui.sync(self)
        future=self.pool.submit(fn)
        def finished(f):
            try: result=f.result(); error=None
            except Exception as exc: result=None; error=str(exc)
            if not self.closing:self.events.done.emit((kind,result,error,epoch))
        future.add_done_callback(finished)
        return True
    def toggle_preview(self):
        self.previewing=not self.previewing
        if self.previewing:
            self.enabled=False; self.epoch+=1; self.pending=None; self.monitor.setText('Resume monitoring'); self.preview_capture()
            self.status.setText('Preview active. Drag an area, then save its tidy reference. Preview stops when monitoring resumes.')
        else:
            self.epoch+=1;self.pending=None;self.status.setText('Preview closed. Automatic monitoring is paused.')
    def preview_capture(self):
        if self.previewing and not self.busy:
            index=self.camera.value(); self.submit(lambda:Camera.capture(index),'preview')
    def reference_ready(self):
        if self.preview.frame is None or time.monotonic()-self.frame_time>120:
            raise ValueError("Open live preview or load a demo reference picture first.")
        if self.frame_kind=="camera" and (not self.previewing or time.monotonic()-self.frame_time>5):
            raise ValueError("Open preview for a fresh reference capture.")
        if self.frame_kind=="demo" and self.mode_name()!="demo":
            raise ValueError("Staged pictures can only be saved in Demo mode.")
        if self.frame_kind not in ("camera","demo"):raise ValueError("Use a fresh preview for reference setup.")
    def load_demo_reference(self):
        if self.mode_name()!="demo":self.status.setText("Switch to Demo to load a staged reference.");return
        from PySide6.QtWidgets import QFileDialog
        import cv2
        path,_=QFileDialog.getOpenFileName(self,"Load labelled demo tidy reference","","Images (*.png *.jpg *.jpeg)")
        if path:
            self.epoch+=1;self.enabled=False;self.previewing=False;self.pending=None;self.monitor.setText("Resume monitoring")
            frame=cv2.imread(path)
            if frame is None:self.status.setText("Could not read demo image.");return
            self.preview.display(frame);self.frame_time=time.monotonic();self.frame_kind="demo"
            self.status.setText("DEMO reference picture loaded. Drag an area and save explicitly as tidy.")
    @guarded
    def add_area(self):
        if self.preview.frame is None or self.preview.rect is None:
            self.status.setText('Open preview and drag a rectangle first.');return
        self.reference_ready()
        png=encode_png(crop(self.preview.frame,self.preview.rect));reason=quality_reason(png)
        if reason:raise ValueError('Reference rejected: '+reason)
        rect=list(self.preview.rect);source=[self.camera.value(),list(self.preview.frame.shape[:2]),self.frame_kind];preferences=self.preferences.text()
        name,ok=QInputDialog.getText(self,'Name area','Area name (for example: desk)')
        if ok and name.strip():
            area_id=self.store.add_area(name.strip(),rect,preferences,png)
            self.store.set_setting('source_'+area_id,source)
            self.refresh();
            import ui
            ui.select_area(self,area_id);self.load_preferences()
            self.status.setText('Tidy reference saved. Use the same fixed camera position.')
    @guarded
    def update_reference(self):
        area=next((a for a in self.store.areas(self.mode_name()) if a['id']==self.selected()),None)
        if area is None:return
        self.reference_ready()
        png=encode_png(crop(self.preview.frame,area['rect']));reason=quality_reason(png)
        if reason:raise ValueError('Reference rejected: '+reason)
        source=[self.camera.value(),list(self.preview.frame.shape[:2]),self.frame_kind]
        if QMessageBox.question(self,'Update reference','Save the displayed area as the shared tidy reference and reset BOTH live and demo tracking?' )==QMessageBox.Yes:
            self.store.update_reference(area['id'],png)
            self.store.set_setting('source_'+area['id'],source)
            self.store.set_setting('last_valid_'+area['id'],0)
            self.refresh();self.load_preferences()
    def cleaned(self,area_id=None):
        area_id=area_id or self.selected()
        if area_id is not None:
            self.store.reset_episode(area_id,self.mode_name())
            if self.mode_name()=='live':self.store.set_setting('last_valid_'+area_id,0)
            self.refresh();self.status.setText('Tracking reset. The tidy reference was kept.')
    def snooze(self,area_id=None):
        area_id=area_id or self.selected()
        if area_id is not None:
            self.store.snooze(area_id,3600,self.mode_name());self.refresh();self.status.setText('Reminder snoozed for one hour.')
    def change_mode(self):
        self.enabled=False;self.epoch+=1;self.monitor.setText('Resume monitoring');self.refresh()
        self.status.setText('Mode changed; monitoring paused. Demo and live tracking are separate.')
    def toggle_monitor(self):
        self.enabled=not self.enabled
        if self.enabled:
            if not self.store.areas(self.mode_name()):self.enabled=False;self.status.setText('Save a tidy area first.');return
            self.previewing=False;self.next_scan=time.monotonic()
        else:self.epoch+=1
        self.monitor.setText('Pause monitoring' if self.enabled else 'Resume monitoring')
        self.status.setText('Monitoring enabled.' if self.enabled else 'Automatic monitoring paused. Manual checks are still available.')
    def tick(self):
        if self.enabled and not self.busy and self.pending is None and time.monotonic()>=self.next_scan:
            self.next_scan=time.monotonic()+(60 if self.mode_name()=='demo' else 3600)
            self.scan()
    def scan(self):
        if self.busy or self.pending is not None:return
        if not self.store.areas(self.mode_name()):self.status.setText('Save a tidy reference first.');return
        self.previewing=False
        self.pending=self.epoch
        self.status.setText('Camera snapshot in 2 seconds. The camera will be released immediately after capture.')
        QTimer.singleShot(2000,self.capture_pending)
    def capture_pending(self):
        epoch=self.pending;self.pending=None
        if epoch!=self.epoch or self.closing or self.close_requested:return
        index=self.camera.value()
        self.start_analysis(lambda:Camera.capture(index))
    def import_demo(self):
        from PySide6.QtWidgets import QFileDialog
        if self.mode_name()!='demo':self.status.setText('Switch to Demo mode to use staged pictures.');return
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Import labelled demo picture','','Images (*.png *.jpg *.jpeg)')
        if path:
            import cv2
            self.start_analysis(lambda:cv2.imread(path))
    def start_analysis(self,frame_fn):
        areas=self.store.areas(self.mode_name()); mode=self.mode_name(); index=self.camera.value();started_at=time.time();epoch=self.epoch;analyzer=self.analyzer
        if not areas:self.status.setText('Save a tidy area first.');return
        def work():
            frame=frame_fn()
            if frame is None:raise ValueError('No image could be read.')
            frame_shape=list(frame.shape[:2])
            results=[]
            for a in areas:
                if epoch!=self.epoch or self.close_requested:break
                source=self.store.get_setting('source_'+a['id'])
                if not source or source[:2]!=[index,frame_shape] or (mode=='live' and source[2]!='camera'):
                    result={'status':'unable_to_assess','evidence':'Camera or image dimensions changed. Explicitly update the shared reference.'}
                else:
                    try:result=analyzer.analyze(Path(a['reference']).read_bytes(),encode_png(crop(frame,a['rect'])),a['preferences'])
                    except Exception as exc:result={'status':'unable_to_assess','evidence':'Area could not be assessed: '+str(exc)[:200]}
                results.append((a,result))
            return frame,results,mode,started_at
        self.status.setText('Analysing locally... First model load can take up to two minutes.')
        if self.enabled:self.next_scan=time.monotonic()+(60 if mode=='demo' else 3600)
        if not self.submit(work,'analysis'):
            self.next_scan=time.monotonic()+5;self.status.setText('Another operation is finishing; next automatic check will retry shortly.')
    def completed(self,message):
        kind,result,error,epoch=message;self.busy=False
        if self.close_requested:self.close();return
        import ui
        ui.sync(self)
        if epoch!=self.epoch:return
        if error:self.status.setText('Unable to assess: '+error);return
        if kind=='preview':self.preview.display(result);self.frame_time=time.monotonic();self.frame_kind='camera';ui.sync(self);return
        frame,results,mode,started_at=result;self.preview.display(frame);self.frame_kind='observation';self.frame_time=0
        descriptions=[]
        for area,observation in results:
            current=next((a for a in self.store.areas(mode) if a['id']==area['id']),None)
            if current is None or current['generation']!=area['generation']:
                descriptions.append(area['name']+': discarded because its baseline or tracking changed.');continue
            last=self.store.get_setting('last_valid_'+area['id'],0)
            hourly_ok=mode=='demo' or observation['status']!='clutter_present' or started_at-last>=3600
            due=False
            if hourly_ok:
                due=self.store.observe(area['id'],observation['status'],observation['evidence'],area['generation'],mode,self.threshold.value())
                current=next((a for a in self.store.areas(mode) if a['id']==area['id']),None)
                if mode=='live' and current and current['generation']==area['generation']:
                    if observation['status']=='clutter_present':self.store.set_setting('last_valid_'+area['id'],started_at)
                    elif observation['status']=='tidy':self.store.set_setting('last_valid_'+area['id'],0)
            else:descriptions.append(area['name']+': assessment only; next hourly tracking check is not due yet.')
            descriptions.append(f"{area['name']}: {observation['status']} - {observation['evidence']}")
            if due:self.notify(area['name'],mode)
        self.status.setText(('DEMO - staged or accelerated observations.\n' if mode=='demo' else '')+'\n'.join(descriptions));self.refresh()
    def notify(self,name,mode):
        from notifications import send_notification
        def dispatch():
            try:send_notification(name,mode)
            except Exception as exc:
                if not self.closing:self.events.toast_error.emit('Reminder active in app; Windows notification unavailable: '+str(exc))
        threading.Thread(target=dispatch,daemon=True).start()
    @guarded
    def delete_data(self):
        if QMessageBox.question(self,'Delete app data','Delete RoomTidy settings, reference images and observation history?')!=QMessageBox.Yes:return
        self.enabled=False;self.previewing=False;self.epoch+=1;self.pending=None
        self.analyzer.close();self.analyzer=Analyzer()
        self.store.delete_data();self.preview.frame=None;self.preview.rect=None;self.preview.clear();self.preview.band.hide();self.preview.setToolTip('')
        self.threshold.blockSignals(True);self.threshold.setValue(30);self.threshold.blockSignals(False)
        self.reduce_motion.blockSignals(True);self.reduce_motion.setChecked(False);self.reduce_motion.blockSignals(False)
        self.preview.setText('Open preview, then drag to select an area.');self.reference_view.setText('Select an area to view its saved tidy reference.');self.preferences.clear();self.frame_kind=None;self.frame_time=0;self.monitor.setText('Resume monitoring');self.refresh();self.status.setText('Local app data deleted. Monitoring paused.')
    def closeEvent(self,event):
        self.enabled=False;self.previewing=False;self.epoch+=1;self.pending=None;self.timer.stop();self.preview_timer.stop()
        if self.busy:
            self.close_requested=True;self.status.setText('Stopping: waiting for camera release / local analysis to finish...')
            self.analyzer.close();event.ignore();return
        self.closing=True;self.analyzer.close();self.pool.shutdown(wait=True,cancel_futures=True);self.store.close()
        event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion')
    from ui_theme import apply_theme
    apply_theme(app)
    window=Window();window.show();sys.exit(app.exec())
