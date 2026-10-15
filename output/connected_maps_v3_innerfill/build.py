"""Add two tapered inner-corner pavement fillets to the preserved 3.9 m version."""
from pathlib import Path
import json,sys,math
import numpy as np
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
OLD=ROOT/'output/connected_maps_v2_width130'
PKG=D/'package';ASSET=PKG/'art/codex_connected_v3_innerfill'
SHAPES=ASSET/'shapes';SHAPES.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'output/china_subject2/beamng_v1'))
from beamng_io import write_dae
sys.path.insert(0,str(ROOT/'output/mountain_hairpin_road/blender_trial_v10_smooth_hairpins'))
from road_profile import curves
MAT='connected_grid_concrete';EARTH='hp3_earth_side'
colors={MAT:{'color':[1,1,1,1]},EARTH:{'color':[.25,.205,.16,1]}}
data=np.load(OLD/'small_road_mesh.npz');tri=data['triangles'];boundary=data['boundary']
verts,inv=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True);faces=inv.reshape(-1,3)
indices=[]
for start in range(0,len(boundary),128):
    dist=np.sum((boundary[start:start+128,None,:]-verts[None,:,:2])**2,axis=2)
    indices.extend(dist.argmin(1))
P=verts[indices]
assert np.max(np.linalg.norm(P[:,:2]-boundary,axis=1))<1e-5
edge_faces={}
for fi,f in enumerate(faces):
    for a,b in zip(f,np.roll(f,-1)):
        edge_faces.setdefault(tuple(sorted([a,b])),[]).append(fi)
cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
gradient=-cross[:,:2]/cross[:,2,None]
G=[]
for i in range(len(P)):
    adjacent=[]
    for a,b in [(indices[i-1],indices[i]),(indices[i],indices[(i+1)%len(P)])]:
        ff=edge_faces[tuple(sorted([a,b]))];assert len(ff)==1
        adjacent.append(gradient[ff[0]])
    G.append(np.mean(adjacent,axis=0))
G=np.array(G)
# Fit a smooth local road tangent plane; tiny export triangles can have noisy
# face gradients even though their vertex heights are continuous.
for i,p in enumerate(P):
    diff=verts[:,:2]-p[:2];dist2=np.sum(diff*diff,axis=1);mask=dist2<6.25
    w=np.exp(-dist2[mask]/(.7**2))
    G[i]=np.linalg.lstsq(np.column_stack([diff[mask],np.ones(mask.sum())])*w[:,None],(verts[mask,2]-p[2])*w,rcond=None)[0][:2]
edge=np.roll(P,-1,axis=0)-P
length=np.linalg.norm(edge[:,:2],axis=1);station=np.r_[0,np.cumsum(length)];perimeter=station[-1]

def triangle(points,material=MAT):
    p=np.array(points);n=np.cross(p[1]-p[0],p[2]-p[0]);size=np.linalg.norm(n)
    if size<1e-10:return None
    n/=size
    return p,np.tile(n,(3,1)),(p[:,:2]+[-1580,-1490])/2,material

current_road=tri.copy()
def fair_surface(top,earth,active):
    # Minimum-energy height extension with the entire original road seam fixed.
    # The free new edge can settle smoothly instead of extrapolating noisy slopes.
    points=np.concatenate([current_road,np.array([t[0] for t in top])]);xy,first,indices=np.unique(np.round(points[:,:,:2].reshape(-1,2),8),axis=0,return_index=True,return_inverse=True)
    z=points[:,:,2].ravel()[first];f=indices.reshape(-1,3)
    originals={tuple(p[:2].round(8)):p[2] for p in current_road.reshape(-1,3)}
    fixed=np.array([tuple(p) in originals for p in xy])
    distance=np.full(len(xy),np.inf)
    for i in range(0,len(xy),128):distance[i:i+128]=np.sqrt(np.min(np.sum((xy[i:i+128,None,:]-P[active,None,:2].transpose(1,0,2))**2,axis=2),axis=1))
    fixed &= distance>1.0
    aa=[];bb=[];ww=[]
    for j in range(3):
        a=f[:,(j+1)%3];b=f[:,(j+2)%3];c=f[:,j]
        u=xy[a]-xy[c];v=xy[b]-xy[c]
        w=.5*np.sum(u*v,axis=1)/np.maximum(np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0]),1e-15)
        aa.extend([a,b]);bb.extend([b,a]);ww.extend([w,w])
    a=np.concatenate(aa);b=np.concatenate(bb);w=np.concatenate(ww)
    diag=np.bincount(a,weights=w,minlength=len(xy));free=~fixed
    def multiply(v):
        r=diag*v-np.bincount(a,weights=w*v[b],minlength=len(xy));r[fixed]=0;return r
    boundary_z=np.where(fixed,z,0);rhs=-multiply(boundary_z)
    x=np.where(free,z,0);r=rhs-multiply(x);q=r/np.maximum(diag,1e-12);q[fixed]=0;p=q.copy();rz=float(r@q)
    for iteration in range(12000):
        ap=multiply(p);den=float(p@ap)
        if abs(den)<1e-25:break
        alpha=rz/den;x+=alpha*p;r-=alpha*ap
        if np.max(np.abs(r/np.maximum(diag,1e-12)))<1e-10:break
        q=r/np.maximum(diag,1e-12);q[fixed]=0;newrz=float(r@q);p=q+newrz/rz*p;rz=newrz
    z=x+boundary_z;points[:,:,2]=z[f]
    heights={tuple(p):h for p,h in zip(xy,z)}
    road_result=points[:len(current_road)]
    result=[triangle(p) for p in points[len(current_road):]]
    newearth=[]
    for p,n,u,m in earth:
        p=p.copy()
        for v in p:
            if v[2]>-13.06+1e-6:v[2]=heights.get(tuple(v[:2].round(8)),v[2]+.015)-.015
        newearth.append(triangle(p,m))
    print('Surface solver iterations',iteration+1,'residual',float(np.max(abs(r/np.maximum(diag,1e-12)))),flush=True)
    return result,newearth,road_result

items=[json.loads(x) for x in (OLD/'package/art/codex_connected_v2_width130/connected.prefab.json').read_text().splitlines()]
probes=[];report=[];drive_routes={};allpatch=[]
for ci,curve in enumerate(curves,1):
    tip=int(np.argmin(np.linalg.norm(P[:,:2]-curve['c'],axis=1)))
    direction=P[tip,:2]-curve['c'];direction/=np.linalg.norm(direction)
    s=(station[:-1]-station[tip]+perimeter/2)%perimeter-perimeter/2
    amount=1.2*np.cos(np.clip(s/5.,-1,1)*np.pi/2)**2
    amount[np.abs(s)>=5]=0
    delta=amount[:,None]*direction
    new=P.copy();new[:,:2]+=delta;new[:,2]+=np.sum(G*delta,axis=1)
    top=[];earth=[]
    for i in range(len(P)):
        j=(i+1)%len(P)
        if amount[i]==0 and amount[j]==0:continue
        # Four transverse rows make the new road surface explicit and inspectable.
        for a,b in zip(np.linspace(0,1,5)[:-1],np.linspace(0,1,5)[1:]):
            row=[P[i]*(1-a)+new[i]*a,P[j]*(1-a)+new[j]*a,P[j]*(1-b)+new[j]*b,P[i]*(1-b)+new[i]*b]
            for points in [[row[0],row[2],row[1]],[row[0],row[3],row[2]]]:
                t=triangle(points)
                if t is None:continue
                assert t[1][0,2]>0,'Fillet must expand outward without folded faces'
                top.append(t)
        a=new[i].copy();b=new[j].copy();a[2]-=.015;b[2]-=.015
        c=b.copy();d=a.copy();c[2]=d[2]=-13.06
        for pts in [[a,b,c],[a,c,d]]:
            t=triangle(pts,EARTH)
            if t is not None:earth.append(t)
    top,earth,current_road=fair_surface(top,earth,amount>.001)
    points=np.array([t[0] for t in top]);norm=np.array([t[1][0] for t in top])
    slopes=np.linalg.norm(norm[:,:2],axis=1)/norm[:,2]
    if slopes.max()>=.45:print('Steep samples',points[slopes>.25][:3].tolist(), 'count',int((slopes>.25).sum()),flush=True)
    assert slopes.max()<.45,('Unacceptably steep fill',ci,slopes.max())
    for name,tris in [('inner_fill_'+str(ci),top),('inner_fill_'+str(ci)+'_earth',earth)]:
        write_dae(SHAPES/(name+'.dae'),name,{1:tris},[],colors)
        items.append(dict(name=name,**{'class':'TSStatic','__parent':'ConnectedMapComponents'},shapeName='/art/codex_connected_v3_innerfill/shapes/'+name+'.dae',position=[-1580,-1490,114],scale=[1,1,1],collisionType='Visible Mesh Final',decalType='Visible Mesh Final'))
    for i,t in enumerate(top):
        p=t[0].mean(0)+[-1580,-1490,114]
        probes.append(dict(route='inner_fill_'+str(ci),s=i,x=float(p[0]),y=float(p[1]),z=float(p[2])))
    area=np.sum(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])[:,2])/2
    report.append(dict(corner=ci,tip_before=P[tip].tolist(),tip_after=new[tip].tolist(),maximum_fill_m=float(amount.max()),added_plan_area_m2=float(area),max_grade=float(slopes.max()),triangles=len(top),seam_height_error_m=0))
    # Saved interpolation grid for subsequent geometry and driving checks.
    np.savez_compressed(D/('corner_'+str(ci)+'.npz'),old=P,new=new,amount=amount,station=s,triangles=points)
    allpatch.extend(top)
# Preserve every original road XY vertex while smoothing a one-metre strip
# adjoining each fill. Move adjacent terrain by the same local height correction.
old_vertices,vertex_indices=np.unique(tri.reshape(-1,3),axis=0,return_index=True)
new_vertices=current_road.reshape(-1,3)[vertex_indices]
dz=new_vertices[:,2]-old_vertices[:,2]
assert np.max(abs(dz))<.4
report.append(dict(local_road_blend_width_m=1.,maximum_existing_road_height_adjustment_m=float(np.max(abs(dz)))))
write_dae(SHAPES/'small_road_filled.dae','small_road_filled',{1:[triangle(p) for p in current_road]},[],colors)
import ast
helper=ast.parse((OLD/'widen.py').read_text())
reader=next(n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name=='read')
import xml.etree.ElementTree as ET
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
exec(compile(ast.Module(body=[reader],type_ignores=[]),'<mesh_reader>','exec'))
for item in items:
    if item.get('name')=='hairpin3_small_road':
        item['shapeName']='/art/codex_connected_v3_innerfill/shapes/small_road_filled.dae'
    elif item.get('name','').startswith('hairpin3_') and item['name']!='hairpin3_main_road':
        source=ROOT/'output/connected_maps_v2_width130/package'/item['shapeName'].lstrip('/')
        if not source.exists():continue
        output=[]
        for group in read(source):
            pp=np.array([t[0] for t in group]);unique,idx=np.unique(pp.reshape(-1,3),axis=0,return_inverse=True)
            for i in range(0,len(unique),96):
                q=unique[i:i+96];d2=np.sum((q[:,None,:2]-old_vertices[None,:,:2])**2,axis=2);near=d2.argmin(1);dist=np.sqrt(d2[np.arange(len(q)),near])
                fade=np.clip(1-dist/1.5,0,1)*np.clip(1-np.maximum(abs(q[:,2]-old_vertices[near,2])-.2,0)/1.8,0,1)
                q[:,2]+=dz[near]*fade
            changed=unique[idx].reshape(pp.shape)
            for p,t in zip(changed,group):
                output.append((p,t[1],t[2],t[3]))
        name=item['name']+'_blended'
        write_dae(SHAPES/(name+'.dae'),name,{1:output},[],{t[3]:{'color':[1,1,1,1]} for t in output})
        item['shapeName']='/art/codex_connected_v3_innerfill/shapes/'+name+'.dae'
(ASSET/'connected.prefab.json').write_text('\n'.join(json.dumps(x,separators=(',',':')) for x in items)+'\n')
root=[json.loads(x) for x in (D/'backup/mission_before.level.json').read_text(encoding='utf-8-sig').splitlines()]
root=[x for x in root if x.get('name')!='codex_connected_v2_width130']
root.append(dict(name='codex_connected_v3_innerfill',**{'class':'SimGroup','__parent':'MissionGroup'}))
level=PKG/'levels/gridmap_v2/main/MissionGroup';(level/'codex_connected_v3_innerfill').mkdir(parents=True,exist_ok=True)
(level/'items.level.json').write_text('\n'.join(json.dumps(x,separators=(',',':')) for x in root)+'\n')
(level/'codex_connected_v3_innerfill/items.level.json').write_text(json.dumps(dict(name='CodexConnectedV3Innerfill',**{'class':'Prefab','__parent':'codex_connected_v3_innerfill'},filename='/art/codex_connected_v3_innerfill/connected.prefab.json',position=[0,0,0],rotationMatrix=[1,0,0,0,1,0,0,0,1],scale=[1,1,1],loadMode='Automatic'))+'\n')
load="""assert(getMissionFilename():find('/gridmap_v2/',1,true),'Load Gridmap V2 first')
loadJsonMaterialsFile('/art/hometown_hairpin_v3/main.materials.json')
loadJsonMaterialsFile('/art/china_subject2_v1/main.materials.json')
loadJsonMaterialsFile('/art/codex_connected_v2_width130/main.materials.json')
local current=scenetree.findObject('CodexConnectedV3Innerfill')
if not current then
  local old=scenetree.findObject('CodexConnectedV2Width130');if old then old:delete() end
  current=assert(spawnPrefab('CodexConnectedV3Innerfill','/art/codex_connected_v3_innerfill/connected.prefab.json','0 0 0','0 0 1 0','1 1 1'))
  scenetree.MissionGroup:addObject(current)
end
local proxy=scenetree.findObject('hairpin3_guardrails_collision');if proxy then proxy:setRenderEnabled(false) end
be:reloadCollision()
return current:getID()
"""
(ASSET/'load.lua').write_text(load);(D/'load.lua').write_text(load)
(D/'fill_probes.json').write_text(json.dumps(probes))
(D/'geometry_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
