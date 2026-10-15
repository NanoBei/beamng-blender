"""Real physics road traversal using BeamNG's script AI; no external forces."""
import json, math, sys, time, urllib.request
from pathlib import Path
D = Path(__file__).resolve().parent
def call(name, arguments=None):
    payload = json.dumps(dict(jsonrpc='2.0', id=1, method='tools/call', params=dict(name=name, arguments=arguments or {}))).encode()
    req = urllib.request.Request('http://127.0.0.1:29292/mcp', payload, {'Content-Type':'application/json'})
    result = json.load(urllib.request.urlopen(req, timeout=35))
    if result.get('error') or result.get('result',{}).get('isError'): raise RuntimeError(result)
    s = '\n'.join(x['text'] for x in result['result']['content'] if x['type']=='text')
    try: return json.loads(s)
    except ValueError: return s
def lua(code): return call('run_lua', {'code':code})
if __name__ == '__main__':
    name = sys.argv[1]
    vehicle_id=int(sys.argv[2])
    query={'id':vehicle_id}
    plan = json.loads((D/'plan.json').read_text())
    nodes = [p[:3] for p in plan['routes'][name]['nodes']]
    if name == 'original_to_subject2': nodes.insert(0,[-1910,-1470,100])
    elif name == 'between_sites':
        nodes.insert(0,[-1634,-1456.5,101])
        tail = nodes[-1]
        nodes.extend([[tail[0]-math.cos(math.radians(25))*s, tail[1]+math.sin(math.radians(25))*s, tail[2]+math.tan(math.radians(10))*s] for s in (1,2,3,4,5,6)])
    path=[];t=0
    for i,p in enumerate(nodes):
        if i: t+=math.dist(p,nodes[i-1])/.6
        path.append(dict(zip(('x','y','z'),p),t=t))
    data=dict(path=path, externalForce=False, loopCount=1, startDelay=3)
    (D/(name+'_drive_path.json')).write_text(json.dumps(data,indent=2))
    before=call('get_vehicle_damage',query)
    command='ai.startFollowing('+ 'jsonDecode([==['+json.dumps(data)+']==])' +')'
    lua('local v=scenetree.findObjectById('+str(vehicle_id)+');v:queueLuaCommand('+json.dumps(command)+');return v:getID()')
    records=[];start=time.monotonic()
    while time.monotonic()-start < t+18:
        time.sleep(8)
        vehicle=call('get_vehicle',query);damage=call('get_vehicle_damage',query)
        p=vehicle['position'];pos=[p['x'],p['y'],p['z']]
        closest=min(range(len(nodes)),key=lambda i:math.dist(pos,nodes[i]))
        record=dict(elapsed=round(time.monotonic()-start,1),vehicle=vehicle,damage=damage,closest_node=closest,route_nodes=len(nodes),distance_to_node=math.dist(pos,nodes[closest]))
        records.append(record);print(json.dumps(record),flush=True)
        if damage.get('damageSum',0)>1 or pos[2]<108:
            print('Stopping: damage or fall detected',flush=True);break
    lua('scenetree.findObjectById('+str(vehicle_id)+'):queueLuaCommand("ai.scriptStop(true,true)");return true')
    report=dict(route=name,externalForce=False,initial_damage=before,records=records,final=call('get_vehicle',query),final_damage=call('get_vehicle_damage',query))
    (D/(name+'_drive_result.json')).write_text(json.dumps(report,indent=2))
    print('Saved drive result',flush=True)
