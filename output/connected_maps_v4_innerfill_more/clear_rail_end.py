"""Remove whole rail parts that encroach on the new pavement, keeping closed parts."""
exec((__import__('pathlib').Path(__file__).parent/'inspect_obstacles.py').read_text().split('p=np.array(')[0])
import sys
sys.path.insert(0,str(ROOT/'output/connected_maps_v3_innerfill/.deps'))
sys.path.insert(0,str(ROOT/'output/china_subject2/beamng_v1'))
from beamng_io import write_dae
import shapely
from shapely.geometry import Polygon
footprint=shapely.unary_union([Polygon(t[:,:2]) for c in [1,2] for t in np.load(D/f'corner_{c}.npz')['triangles']]).buffer(.15)
asset=D/'package/art/codex_connected_v4_innerfill_more';report={}
for stem in ['hairpin3_guardrails_visual','hairpin3_guardrails_collision']:
    ts=[t for g in read(asset/'shapes'/f'{stem}_blended.dae') for t in g]
    pp=np.array([t[0] for t in ts]);uv,ix=np.unique(pp.reshape(-1,3).round(5),axis=0,return_inverse=True);faces=ix.reshape(-1,3)
    parent=list(range(len(uv)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for f in faces:
        for v in f[1:]:parent[root(v)]=root(f[0])
    groups={}
    for i,f in enumerate(faces):groups.setdefault(root(f[0]),[]).append(i)
    remove=set();parts=[];retained=[]
    for ids in groups.values():
        points=pp[ids].reshape(-1,3);hull=shapely.MultiPoint(points[:,:2]).convex_hull
        if hull.intersects(footprint):
            parts.append(dict(triangles=len(ids),bounds_min=points.min(0).tolist(),bounds_max=points.max(0).tolist()))
            remove.update(ids)
            # The visible W-beam is one continuous mesh. Keep its upstream
            # length and cut only the final bay, matching the collision panels.
            if stem.endswith('visual') and np.ptp(points[:,0])>2:
                cutoff=22.30
                for ti in ids:
                    p,n,u,m=ts[ti];poly=list(np.column_stack([p,n,u]));out=[]
                    for a,b in zip(poly,poly[1:]+poly[:1]):
                        inside_a=a[0]<=cutoff;inside_b=b[0]<=cutoff
                        if inside_a:out.append(a)
                        if inside_a!=inside_b:out.append(a+(b-a)*(cutoff-a[0])/(b[0]-a[0]))
                    for j in range(1,len(out)-1):
                        q=np.array([out[0],out[j],out[j+1]])
                        retained.append((q[:,:3],q[:,3:6],q[:,6:],m))
                parts[-1]['action']='Trim only final bay at local x=22.30; retain upstream beam'
    report[stem]=dict(total_parts=len(groups),removed_parts=parts,removed_triangles=len(remove))
    print(stem,report[stem])
    # Never silently remove the whole rail assembly.
    assert len(remove)<len(ts)*.4
    result=[t for i,t in enumerate(ts) if i not in remove]+retained
    write_dae(asset/'shapes'/f'{stem}_clear.dae',stem+'_clear',{1:result},[],{t[3]:{'color':[1,1,1,1]} for t in result})
    p=asset/'connected.prefab.json';p.write_text(p.read_text().replace(stem+'_blended.dae',stem+'_clear.dae'))
(D/'rail_clearance_checks.json').write_text(json.dumps(report,indent=2))
