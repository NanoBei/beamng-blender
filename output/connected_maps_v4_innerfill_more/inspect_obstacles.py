from pathlib import Path
import ast,json,xml.etree.ElementTree as ET
import numpy as np
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
t=ast.parse((ROOT/'output/connected_maps_v2_width130/widen.py').read_text())
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='read'],type_ignores=[]),'<reader>','exec'))
p=np.array([-1555.9472157012,-1456.8683138034,111.63893428736])-[-1580,-1490,114]
for path in (D/'package/art/codex_connected_v4_innerfill_more/shapes').glob('*blended.dae'):
    tris=np.array([q[0] for g in read(path) for q in g]);a=tris[:,0];u=tris[:,1]-a;v=tris[:,2]-a
    det=u[:,0]*v[:,1]-u[:,1]*v[:,0];ok=abs(det)>1e-12
    tris=tris[ok];a=a[ok];u=u[ok];v=v[ok];det=det[ok];d=p-a
    b=(d[:,0]*v[:,1]-d[:,1]*v[:,0])/det;c=(u[:,0]*d[:,1]-u[:,1]*d[:,0])/det
    hit=(b>=0)&(c>=0)&(b+c<=1);z=(a[:,2]+b*u[:,2]+c*v[:,2])[hit]
    if len(z):print(path.name,z.tolist())
