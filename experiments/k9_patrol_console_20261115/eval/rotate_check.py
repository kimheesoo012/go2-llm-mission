import sqlite3,json,cv2,sys,numpy as np
from pathlib import Path
from ultralytics import YOLO
sys.path.insert(0,'v3');from posture_rules_v3 import classify_posture as c
R=Path('wt/k9_patrol_console');db=sqlite3.connect(R/'data/records.sqlite3');model=YOLO(str(R/'yolo11n-pose.pt'))
def det(im,conf=.45):
    r=model.predict(im,conf=conf,classes=[0],imgsz=512,verbose=False)[0]
    return [(float(b.conf[0]),[float(v) for v in b.xyxy[0].tolist()],r.keypoints.data[j].tolist()) for j,b in enumerate(r.boxes)] if r.boxes is not None else []
def back(dets,k,W,H):
    out=[]
    for cf,b,kp in dets:
        if k==1:   # 원본을 시계방향 90도 회전한 영상 -> 원본: x=y', y=H-1-x'
            f=lambda x,y:(y,H-1-x)
        else:      # 반시계 90도 -> 원본: x=W-1-y', y=x'
            f=lambda x,y:(W-1-y,x)
        p=[f(b[0],b[1]),f(b[2],b[3])];bb=[min(p[0][0],p[1][0]),min(p[0][1],p[1][1]),max(p[0][0],p[1][0]),max(p[0][1],p[1][1])]
        out.append((cf,bb,[[*f(x,y),s] for x,y,s in kp]))
    return out
res=[];tiles=[]
for rid in sys.argv[1:]:
    clip=db.execute("select clip from records where id like ?",(rid+'%',)).fetchone()[0]
    cap=cv2.VideoCapture(str(R/'data/media'/Path(clip).name));fps=cap.get(cv2.CAP_PROP_FPS) or 10;i=0
    while True:
        ok,im=cap.read()
        if not ok:break
        if i%max(1,round(fps*.5))==0:
            H,W=im.shape[:2]
            n=det(im);a=back(det(cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)),1,W,H);b=back(det(cv2.rotate(im,cv2.ROTATE_90_COUNTERCLOCKWISE)),2,W,H)
            row=[rid,i]
            for name,ds in (('norm',n),('cw',a),('ccw',b)):
                row.append([(round(cf,2),c(kp,bx)['code']) for cf,bx,kp in ds])
            print(row);res.append(row)
        i+=1
