from pathlib import Path
import json
import numpy as np
D=Path(__file__).resolve().parent
tri=np.load(D/'small_road_mesh.npz')['triangles']
samples=[]
for i,t in enumerate(tri):
    # All faces in the newly widened road are checked at their interiors.
    p=t.mean(0)
    samples.append(dict(route='mountain_small',s=i,x=float(p[0]-1580),y=float(p[1]-1490),z=float(p[2]+114)))
for x in np.linspace(1.13,39.13,20):
    for y in np.linspace(42.13,48.37,14):
        samples.append(dict(route='mountain_main',s=float(x),x=float(x-1580),y=float(y-1490),z=114.))
(D/'mountain_probes.json').write_text(json.dumps(samples))
print(len(samples),'mountain probes')
