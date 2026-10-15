"""Generate collision probes from shipped geometry, independently of build scripts."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
NS = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
checks = []

def probe_mesh(asset, name, offset, count, collision=False):
    doc = ET.parse(ROOT / 'package/art' / asset / 'shapes' / (name + '.dae'))
    triangles = []
    for geo in doc.findall('.//c:library_geometries/c:geometry', NS):
        is_collision = geo.get('name', '').lower().startswith('colmesh')
        if collision != is_collision:
            continue
        mesh = geo.find('c:mesh', NS)
        arrays = {}
        for src in mesh.findall('c:source', NS):
            data = src.find('c:float_array', NS)
            stride = int(src.find('c:technique_common/c:accessor', NS).get('stride'))
            arrays[src.get('id')] = np.fromstring(data.text, sep=' ').reshape(-1, stride)
        vertices = {v.get('id'): v.find('c:input[@semantic="POSITION"]', NS).get('source')[1:]
                    for v in mesh.findall('c:vertices', NS)}
        for elem in mesh.findall('c:triangles', NS):
            inputs = elem.findall('c:input', NS)
            width = max(int(i.get('offset')) for i in inputs) + 1
            vi = next(i for i in inputs if i.get('semantic') == 'VERTEX')
            ids = np.fromstring(elem.find('c:p', NS).text, sep=' ', dtype=int).reshape(-1, width)
            points = arrays[vertices[vi.get('source')[1:]]]
            triangles.extend(points[ids[:, int(vi.get('offset'))]].reshape(-1, 3, 3))
    triangles = np.array(triangles)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    upward = normals[:, 2] / np.maximum(np.linalg.norm(normals, axis=1), 1e-10) > .8
    triangles = triangles[upward]
    for i in np.linspace(0, len(triangles) - 1, count).astype(int):
        p = triangles[i].mean(axis=0) + np.array(offset)
        if name == 'road_flat_asphalt' and abs(p[0]+1668.4910971)<.001:
            print('Edge probe triangle:', triangles[i].tolist())
        checks.append({'part': name, 'x': float(p[0]), 'y': float(p[1]), 'z': float(p[2])})

for name, count in [('road_flat_concrete',35), ('road_flat_asphalt',35), ('road_hillramp',30), ('curbs',12), ('fence',8)]:
    probe_mesh('china_subject2_v1',name,[-1700,-1500,101],count,True)
for name, count in [('main_road',12), ('small_road',40), ('guardrails_collision',12)]:
    probe_mesh('hometown_hairpin_v3',name,[-1580,-1490,114],count)
report = json.loads((ROOT.parent / 'mountain_hairpin_road/beamng_hairpin_test_v3/export_report.json').read_text())
for key, label in [('small_drain_floor_checks','drain_floor'), ('filled_shoulder_checks','filled_shoulder')]:
    for p in report[key]:
        checks.append({'part':label,'x':p['xy'][0]-1580,'y':p['xy'][1]-1490,'z':p.get('floor_z',p.get('z'))+114})
payload = json.dumps(checks,separators=(',',':'))
lua = '''local samples=jsonDecode([==[PAYLOAD]==])
local failed={};local maxError=0;local byPart={}
for _,p in ipairs(samples) do
  local height=160-castRayStatic(vec3(p.x,p.y,160),vec3(0,0,-1),90)
  local err=math.abs(height-p.z)
  maxError=math.max(maxError,err)
  byPart[p.part]=(byPart[p.part] or 0)+1
  if err>0.025 then failed[#failed+1]={part=p.part,x=p.x,y=p.y,expected=p.z,actual=height,error=err} end
end
local objects={}
for _,id in ipairs(scenetree.findClassObjects('TSStatic')) do
  local o=scenetree.findObject(id);local n=o:getName()
  if n:find('c1_',1,true)==1 or n:find('hairpin3_',1,true)==1 then
    objects[#objects+1]={name=n,render=o:isRenderEnabled(),collision=o:getField('collisionType',0)}
  end
end
return jsonEncode({samples=#samples,failed=failed,maxError=maxError,byPart=byPart,objects=objects,level=getMissionFilename(),version=beamng_version})
'''.replace('PAYLOAD',payload)
(ROOT / 'verify_runtime.lua').write_text(lua,encoding='utf-8')
print(f'Generated {len(checks)} independent collision probes')
