import sqlite3,json,cv2,sys
from pathlib import Path
exec(open('rot.py').read().split("res=[];tiles=[]")[0])
def iou(a,b):
    x0,y0,x1,y1=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]);i=max(0,x1-x0)*max(0,y1-y0)
    return i/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-i+1e-9)
out=[];Path('rotframes').mkdir(exist_ok=True)
for rid,clip in db.execute("select id,clip from records where time like '2026-11-14%' and clip is not null and clip!='' order by time"):
    cap=cv2.VideoCapture(str(R/'data/media'/Path(clip).name));fps=cap.get(cv2.CAP_PROP_FPS) or 10;i=0
    while True:
        ok,im=cap.read()
        if not ok:break
        if i%max(1,round(fps*.5))==0:
            H,W=im.shape[:2];n=det(im);lo=det(im,.25)
            a=back(det(cv2.rotate(im,cv2.ROTATE_90_CLOCKWISE)),1,W,H);b=back(det(cv2.rotate(im,cv2.ROTATE_90_COUNTERCLOCKWISE)),2,W,H)
            extra=[]
            for cf,bx,kp in sorted(a+b,key=lambda t:-t[0]):
                if all(iou(bx,o[1])<.3 for o in n) and all(iou(bx,e[1])<.3 for e in extra):extra.append((cf,bx,kp))
            name=f'{rid[:8]}_{i:04d}'
            out.append(dict(frame=name,norm=[dict(conf=x[0],box=x[1],kp=x[2]) for x in n],low=[dict(conf=x[0],box=x[1],kp=x[2]) for x in lo],extra=[dict(conf=x[0],box=x[1],kp=x[2]) for x in extra]))
            if extra or len(lo)>len(n):cv2.imwrite(f'rotframes/{name}.jpg',cv2.resize(im,(480,270)))
        i+=1
json.dump(out,open('rotall.json','w'))
