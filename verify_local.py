import time, json
import numpy as np, cv2
from vision import Analyzer, Camera, encode_png
try:
    f=Camera.capture(0)
    print('CAMERA_CAPTURE_RELEASE',f.shape,'brightness',round(float(f.mean()),2),flush=True)
except Exception as e: print('CAMERA_ERROR',str(e),flush=True)
a=Analyzer()
ref=np.full((384,512,3),210,np.uint8)
cv2.rectangle(ref,(20,30),(480,350),(110,130,150),4)
cv2.rectangle(ref,(60,80),(200,220),(25,25,220),-1)
cv2.putText(ref,'DESK',(270,65),cv2.FONT_HERSHEY_SIMPLEX,.7,(20,20,20),2)
current=ref.copy()
cv2.circle(current,(350,200),60,(220,50,20),-1)
try:
    for name,image in [('same_reference',ref),('added_blue_circle',current),('dark',np.zeros_like(ref)),('blocked',np.full_like(ref,80))]:
        start=time.monotonic()
        result=a.analyze(encode_png(ref),encode_png(image),'Red square is allowed. Blue circular objects should be removed.')
        print(name,json.dumps(result),'seconds',round(time.monotonic()-start,2),flush=True)
finally:a.close()
