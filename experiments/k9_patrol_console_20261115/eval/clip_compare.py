import json,sys,collections,importlib.util
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m.classify_posture
v2=load('v2','/home/claude/src/capstone/k9_patrol_console/posture_rules.py');v3=load('v3','/home/claude/work/shoot/v3/posture_rules_v3.py')
D=json.load(open('clipdets.json'));c2=collections.Counter();c3=collections.Counter();cross=collections.Counter();r3=collections.Counter();per=collections.defaultdict(lambda:[collections.Counter(),collections.Counter()])
res=[]
for o in D:
    for j,d in enumerate(o['dets']):
        a=v2(d['kp'],d['box']);b=v3(d['kp'],d['box'])
        c2[a['code']]+=1;c3[b['code']]+=1;cross[(a['code'],b['code'])]+=1
        if b['code']=='unknown':r3[b['reason']]+=1
        per[o['rid']][0][a['code']]+=1;per[o['rid']][1][b['code']]+=1
        res.append((o['frame'],j,a['code'],b['code'],b['reason']))
print('clips',len({o['rid'] for o in D}),'v2',dict(c2),'\nv3',dict(c3));print(sorted(cross.items()));
for k,v in r3.most_common():print(v,k)
json.dump(res,open('clipres.json','w'),ensure_ascii=False)
for rid,(a,b) in per.items():print(rid,dict(a),'->',dict(b))
