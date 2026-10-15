from pathlib import Path
import json
from drive_check import lua
D=Path(__file__).resolve().parent
samples=json.loads((D/'fill_probes.json').read_text())
failed=[];max_error=0
for start in range(0,len(samples),1000):
    batch=samples[start:start+1000]
    code='''local samples=jsonDecode([==[PAYLOAD]==]);local bad={};local maxError=0
    for _,p in ipairs(samples) do
      local h=180-castRayStatic(vec3(p.x,p.y,180),vec3(0,0,-1),100)
      local e=math.abs(h-p.z);maxError=math.max(maxError,e)
      if e>.035 then p.actual=h;p.error=e;bad[#bad+1]=p end
    end
    return jsonEncode({bad=bad,maxError=maxError})'''.replace('PAYLOAD',json.dumps(batch))
    r=lua(code);failed.extend(r['bad'] or []);max_error=max(max_error,r['maxError'])
result=dict(samples=len(samples),failCount=len(failed),maxError=max_error,failed=failed)
(D/'fill_collision_checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(samples=len(samples),failCount=len(failed),maxError=max_error,firstFailures=failed[:12]),indent=2))
