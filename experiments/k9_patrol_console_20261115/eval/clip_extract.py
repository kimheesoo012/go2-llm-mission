import sqlite3,json,cv2,sys
from pathlib import Path
from ultralytics import YOLO
R=Path('wt/k9_patrol_console');db=sqlite3.connect(R/'data/records.sqlite3')
model=YOLO(str(R/'yolo11n-pose.pt'));out=[];Path('frames').mkdir(exist_ok=True)
rows=db.execute("select id,time,clip from records where time like '2026-11-14%' and clip is not null and clip!='' order by time").fetchall()
print(len(rows),rows[:2])
for rid,t,clip in rows:
    p=R/'data'/'media'/Path(clip).name
    if not p.exists():print('missing',clip);continue
    cap=cv2.VideoCapture(str(p));fps=cap.get(cv2.CAP_PROP_FPS) or 10;every=max(1,round(fps*.5));i=0
    while True:
        ok,im=cap.read()
        if not ok:break
        if i%every==0:
            r=model.predict(im,conf=.45,classes=[0],imgsz=512,verbose=False)[0]
            name=f'{rid[:8]}_{i:04d}'
            dets=[dict(conf=float(b.conf[0]),box=[float(v) for v in b.xyxy[0].tolist()],kp=r.keypoints.data[j].tolist()) for j,b in enumerate(r.boxes)] if r.boxes is not None else []
            out.append(dict(frame=name,rid=rid[:8],t=t,sec=i/fps,size=im.shape[:2],dets=dets))
            if dets:cv2.imwrite(f'frames/{name}.jpg',cv2.resize(im,(480,270)))
        i+=1
    cap.release()
json.dump(out,open('clipdets.json','w'));print(len(out),sum(1 for o in out if o['dets']),sum(len(o['dets']) for o in out))
