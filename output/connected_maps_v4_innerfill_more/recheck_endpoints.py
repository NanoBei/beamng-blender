from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'connected_maps_v3_innerfill'))
from drive_check import lua
D=Path(__file__).resolve().parent
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
print('Rechecked tapered endpoints:',len(checks))
