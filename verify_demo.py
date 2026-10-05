import os,sys,time
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
root=Path(__file__).resolve().parent
os.environ['LOCALAPPDATA']=str(root/'.demo-verification-local')
import cv2
from PySide6.QtWidgets import QApplication
from app import Window
application=QApplication([]);w=Window();w.mode.setCurrentIndex(1);w.threshold.setValue(3)
ref=(root/'demo'/'tidy.png').read_bytes()
aid=w.store.add_area('synthetic desk',[0,0,1,1],'Red square is allowed. Blue circular objects should be removed.',ref)
w.store.set_setting('source_'+aid,[0,[384,512],'demo'])
notifications=[];w.notify=lambda name,mode:notifications.append((name,mode))
try:
    for name in ['clutter','dark','blocked','clutter','clutter','clutter','tidy']:
        a=w.store.areas('demo')[0];frame=cv2.imread(str(root/'demo'/f'{name}.png'))
        result=w.analyzer.analyze(ref,(root/'demo'/f'{name}.png').read_bytes(),a['preferences'])
        w.completed(('analysis',(frame,[(a,result)],'demo',time.time()),None,w.epoch))
        current=w.store.areas('demo')[0]
        print(name,result['status'],'count',current['count'],'alerts',len(notifications),flush=True)
    assert len(notifications)==1
    assert w.store.areas('demo')[0]['count']==0
    w.store.delete_data()
    assert not w.store.areas('demo')
    print('GUI tracking golden path and delete PASS',flush=True)
finally:w.close()
