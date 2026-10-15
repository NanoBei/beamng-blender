from collections import Counter
from pathlib import Path
import json,math
import numpy as np
from inspect_mesh import read_mesh

root=Path(__file__).parent
_,v,f=read_mesh(root/'package/art/hairpin_road/shapes/road_wide20.dae')
counts=Counter(tuple(sorted(e)) for t in f for e in [(t[0],t[1]),(t[1],t[2]),(t[2],t[0])])
edges=np.array([e for e,c in counts.items() if c==1])
a=v[edges[:,0],:2];d=v[edges[:,1],:2]-a
def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
def measure(c,n):
    den=cross(np.broadcast_to(n,d.shape),d)
    valid=abs(den)>1e-10
    t=np.zeros(len(d));s=np.zeros(len(d))
    t[valid]=cross(a[valid]-c,d[valid])/den[valid]
    s[valid]=cross(a[valid]-c,n)/den[valid]
    hits=np.unique(np.round(t[valid & (s>=-1e-6)&(s<=1+1e-6)&(abs(t)<4)],6))
    assert len(hits)==2,(c,hits)
    return float(hits[1]-hits[0])

p=np.array([11.,44.]);h=-25.;checks=[]
for kind,length,turn in [('line',20,0),('arc',1.9875,-145),('line',12,0),('arc',1.9875,145),('line',16,0)]:
    u=np.array([math.cos(math.radians(h)),math.sin(math.radians(h))])
    if kind=='line':
        end=p+length*u;c=p+.7*length*u;n=np.array([-u[1],u[0]])
        width=measure(c,n);assert abs(width-3.33)<.0001,width
        checks.append({'centerXY':c.tolist(),'normalXY':n.tolist(),'widthM':width})
    else:
        sign=np.sign(turn);c=p+sign*length*np.array([-u[1],u[0]])
        angle=math.atan2(p[1]-c[1],p[0]-c[0])+math.radians(turn)
        end=c+length*np.array([math.cos(angle),math.sin(angle)])
    p=end;h+=turn
main=measure(np.array([7.,44.]),np.array([0.,1.]));assert abs(main-4)<1e-6
report={'mainWidthM':main,'slopes':checks,'method':'intersections with exported road mesh boundary'}
(root/'measured_widths.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
