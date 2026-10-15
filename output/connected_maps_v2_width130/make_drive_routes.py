from pathlib import Path
import json,sys,numpy as np
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[1]/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
from road_profile import segments,profile
plan=json.loads((D/'plan.json').read_text())
plan['routes']['wide_main_test']={'nodes':[[float(x-1580),-1443.,114.] for x in np.linspace(3,40,75)]}
seg=segments[-1];nodes=[]
connector=np.array(plan['routes']['between_sites']['nodes'])
for s in np.linspace(5,24,77):
    q=seg['start']+s*seg['t']+.85*seg['n']
    if s<=16:z=114+profile(seg['s']+s)+.85*.02/1.3
    else:
        dist=np.linalg.norm(connector[:,:2]-(q+[-1580,-1490]),axis=1)
        i=dist.argmin();z=connector[i,2]+.85*.02/1.3
    nodes.append([float(q[0]-1580),float(q[1]-1490),float(z)])
plan['routes']['wide_small_join_test']={'nodes':nodes}
(D/'plan.json').write_text(json.dumps(plan,indent=2))
