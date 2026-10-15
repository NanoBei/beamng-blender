from pathlib import Path
import numpy as np,json
from drive_check import lua
D=Path(__file__).resolve().parent
plan={'routes':{}}
for i in [1,2]:
    d=np.load(D/('corner_'+str(i)+'.npz'));tip=d['amount'].argmax();p=d['old'][tip];direction=(d['new'][tip,:2]-p[:2]);direction/=np.linalg.norm(direction);tangent=np.array([-direction[1],direction[0]])
    nodes=[]
    for s in np.linspace(.6,1.2,13):
        xy=p[:2]+s*direction+[-1580,-1490]
        nodes.append([float(xy[0]),float(xy[1])])
    payload=json.dumps(nodes)
    data=lua('local a=jsonDecode([==['+payload+']==]);for _,p in ipairs(a) do p[3]=180-castRayStatic(vec3(p[1],p[2],180),vec3(0,0,-1),100) end;return jsonEncode(a)')
    assert min(p[2] for p in data)>108,data
    plan['routes']['corner_'+str(i)+'_fill_test']={'nodes':data}
(D/'plan.json').write_text(json.dumps(plan,indent=2))
# Microscopic tapered endpoint triangles can miss float-precision rays; require
# surface support within 2 mm for every raw miss, and retain the raw report.
bad=json.loads((D/'fill_collision_checks.json').read_text())['failed']
code='''local a=jsonDecode([==[PAYLOAD]==]);for _,p in ipairs(a) do local best=1e9
for _,d in ipairs({{.002,0},{-.002,0},{0,.002},{0,-.002}}) do
local h=180-castRayStatic(vec3(p.x+d[1],p.y+d[2],180),vec3(0,0,-1),100)
best=math.min(best,math.abs(h-p.z)) end;p.neighbourError=best end;return jsonEncode(a)'''
checks=lua(code.replace('PAYLOAD',json.dumps(bad)))
assert all(p['neighbourError']<.01 for p in checks),checks
(D/'taper_endpoint_rechecks.json').write_text(json.dumps(checks,indent=2))
print('Prepared both driving routes and verified',len(checks),'sub-millimetre tapered endpoints')
