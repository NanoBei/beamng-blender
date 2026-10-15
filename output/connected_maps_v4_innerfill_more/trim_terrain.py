"""Exact footprint subtraction, interpolating 3D terrain attributes."""
from pathlib import Path
import json,sys,ast
import numpy as np
import xml.etree.ElementTree as ET
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'output/connected_maps_v3_innerfill/.deps'))
import shapely
from shapely.geometry import Polygon,LineString
sys.path.insert(0,str(ROOT/'output/china_subject2/beamng_v1'))
from beamng_io import write_dae
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
for file,names in [('connected_maps_v2_width130/widen.py',['read']),('connected_maps_v1/build.py',['clip_half'])]:
    tree=ast.parse((ROOT/'output'/file).read_text(encoding='utf-8-sig'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<mesh_helpers>','exec'))
pieces=[]
for corner in [1,2]:
    for t in np.load(D/('corner_'+str(corner)+'.npz'))['triangles']:pieces.append(Polygon(t[:,:2]))
footprint=shapely.unary_union(pieces).buffer(.000001)
asset=D/'package/art/codex_connected_v4_innerfill_more';counts={}
for stem in ['hairpin3_terrain','hairpin3_earth_sides']:
    source=asset/'shapes'/(stem+'_blended.dae');result=[];affected=0
    for group in read(source):
        for p,n,u,m in group:
            cross=np.cross(p[1]-p[0],p[2]-p[0]);attrs=np.column_stack([p,n,u])
            if abs(cross[2])<1e-10:
                edges=p[[1,2,0],:2]-p[:,:2];direction=edges[np.argmax(np.linalg.norm(edges,axis=1))]
                if np.linalg.norm(direction)<1e-12:result.append((p,n,u,m));continue
                direction/=np.linalg.norm(direction);s=p[:,:2]@direction;base=p[0,:2]-s[0]*direction
                line=LineString([base+s.min()*direction,base+s.max()*direction])
                if not line.intersects(footprint):result.append((p,n,u,m));continue
                affected+=1
                for part in shapely.get_parts(line.difference(footprint)):
                    if part.geom_type!='LineString':continue
                    values=np.asarray(part.coords)@direction
                    poly=clip_half(list(attrs),direction,float(values.min()),True)
                    poly=clip_half(poly,direction,float(values.max()),False)
                    for j in range(1,len(poly)-1):
                        v=np.array([poly[0],poly[j],poly[j+1]])
                        if np.linalg.norm(np.cross(v[1,:3]-v[0,:3],v[2,:3]-v[0,:3]))>1e-10:result.append((v[:,:3],v[:,3:6],v[:,6:],m))
            else:
                poly=Polygon(p[:,:2])
                if not poly.intersects(footprint):result.append((p,n,u,m));continue
                affected+=1;remaining=poly.difference(footprint)
                mat=np.column_stack([p[1,:2]-p[0,:2],p[2,:2]-p[0,:2]])
                for face in shapely.get_parts(shapely.constrained_delaunay_triangles(remaining)):
                    q=np.asarray(face.exterior.coords)[:3]
                    bary=np.linalg.solve(mat,(q-p[0,:2]).T).T
                    v=np.column_stack([1-bary.sum(1),bary])@attrs
                    if np.cross(v[1,:3]-v[0,:3],v[2,:3]-v[0,:3])[2]*cross[2]<0:v=v[::-1]
                    result.append((v[:,:3],v[:,3:6],v[:,6:],m))
    write_dae(asset/'shapes'/(stem+'_trimmed.dae'),stem+'_trimmed',{1:result},[],{t[3]:{'color':[1,1,1,1]} for t in result})
    counts[stem]=dict(affected=affected,triangles=len(result));print(stem,counts[stem],flush=True)
prefab=asset/'connected.prefab.json';s=prefab.read_text()
for stem in counts:s=s.replace(stem+'_blended.dae',stem+'_trimmed.dae')
prefab.write_text(s)
(D/'terrain_trim_checks.json').write_text(json.dumps(counts,indent=2))
