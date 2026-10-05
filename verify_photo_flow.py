"""Actual local-model synthetic walkthrough check; no camera images or cloud APIs."""
import os,time,json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from photo_demo import PhotoDemoWindow,STEPS,PHOTOS
from vision import MODEL_NAME
from ui_theme import apply_theme
output_dir=Path(os.environ.get('ROOMTIDY_VERIFICATION_OUTPUT',str(Path(__file__).parent/'.photo-verification-output')))
output_dir.mkdir(parents=True,exist_ok=True)
application=QApplication([]);apply_theme(application)
window=PhotoDemoWindow(data_root=Path(__file__).parent/'.photo-verification-profile');window.show()
results=[]
try:
 print('MODEL',MODEL_NAME,flush=True)
 window.start_walkthrough()
 if not window.guide_area:raise RuntimeError(window.status.toolTip())
 for index,step in enumerate(STEPS):
  started=time.monotonic();window.next_step()
  while window.busy and time.monotonic()-started<240:
   application.processEvents();time.sleep(.02)
  application.processEvents()
  if window.busy:raise RuntimeError('Timed out waiting for local analysis')
  area=window.store.areas('demo')[0]
  actual=window.store.history('demo')[0]
  row={'step':index+1,'status':actual['status'],'count':area['count'],'alerted':area['alerted'],'seconds':round(time.monotonic()-started,2),'evidence':actual['evidence']}
  results.append(row);print(json.dumps(row),flush=True)
  if index==4:window.grab().save(str(output_dir/'roomtidy-photo-reminder.png'))
 window.grab().save(str(output_dir/'roomtidy-photo-finished.png'))
 (output_dir/'results.json').write_text(json.dumps({'model':MODEL_NAME,'observations':results},indent=2),encoding='utf-8')
 assert [(r['status'],r['count']) for r in results]==[(s[2],s[3]) for s in STEPS], 'Actual observations did not match walkthrough targets; results retained honestly.'
 assert [r['alerted'] for r in results]==[False,False,False,False,True,True,False]
 print('SYNTHETIC_LOCAL_FLOW_PASS',flush=True)
finally:
 window.close()
 while window.busy:application.processEvents();time.sleep(.02)
 application.processEvents()
