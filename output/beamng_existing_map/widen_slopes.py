"""Widen the original slope mesh across its centerline, retaining the 4 m main road."""
from pathlib import Path
import json, math
import xml.etree.ElementTree as ET
import numpy as np
from inspect_mesh import read_mesh, NS

ROOT=Path(__file__).parent
SHAPES=ROOT/'package/art/hairpin_road/shapes'
ET.register_namespace('',NS['c'])
HALF=2.775/2

# Original route confirmed by fitted outer boundary circles (R=3.375 m).
segments=[]; p=np.array([11.,44.]); heading=-25.
for kind,length,turn in [('line',20,0),('arc',1.9875,-145),('line',12,0),('arc',1.9875,145),('line',16,0)]:
    h=math.radians(heading); u=np.array([math.cos(h),math.sin(h)])
    if kind=='line':
        end=p+length*u
        segments.append((kind,p.copy(),end.copy()))
    else:
        sign=np.sign(turn); c=p+sign*length*np.array([-u[1],u[0]])
        start=math.atan2(p[1]-c[1],p[0]-c[0]); sweep=math.radians(turn)
        end=c+length*np.array([math.cos(start+sweep),math.sin(start+sweep)])
        segments.append((kind,c,length,start,sweep))
    p=end; heading+=turn

def closest(xy):
    candidates=[]
    for seg in segments:
        if seg[0]=='line':
            _,a,b=seg; d=b-a
            t=np.clip(((xy-a)*d).sum(1)/(d*d).sum(),0,1)
            q=a+t[:,None]*d
        else:
            _,c,r,a,sweep=seg
            angle=np.arctan2(xy[:,1]-c[1],xy[:,0]-c[0])
            # Compare radial projection (only inside the arc) and both endpoints.
            delta=((angle-a)*np.sign(sweep))%(2*np.pi)
            angle=a+np.clip(delta,0,abs(sweep))*np.sign(sweep)
            choices=np.stack([c+r*np.c_[np.cos(angle),np.sin(angle)],
                              np.broadcast_to(c+r*np.array([math.cos(a),math.sin(a)]),xy.shape),
                              np.broadcast_to(c+r*np.array([math.cos(a+sweep),math.sin(a+sweep)]),xy.shape)],axis=1)
            idx=np.argmin(((choices-xy[:,None,:])**2).sum(2),axis=1)
            q=choices[np.arange(len(xy)),idx]
        candidates.append(q)
    choices=np.stack(candidates,axis=1)
    idx=np.argmin(((choices-xy[:,None,:])**2).sum(2),axis=1)
    return choices[np.arange(len(xy)),idx]

def deform(v):
    xy=v[:,:2]; q=closest(xy); delta=xy-q
    dist=np.linalg.norm(delta,axis=1)
    # Exactly +20% over the full road width, fading out in the adjacent terrain.
    t=np.clip((dist-1.45)/(2.2-1.45),0,1)
    weight=1-t*t*(3-2*t)
    shift=.2*delta*weight[:,None]
    # The approved bends contain filled inner corners reaching the arc centers.
    # Keep this small inner core continuous instead of turning it inside out.
    for seg in segments:
        if seg[0]=='arc':
            r=np.linalg.norm(xy-seg[1],axis=1)
            core=np.clip((r-.6)/.7,0,1)
            shift*= (core*core*(3-2*core))[:,None]
    # Open the junction along the y=42 main-road edge; retain main-road y=42..46.
    t=np.clip((xy[:,1]-40)/2,0,1); blend=t*t*(3-2*t)
    shift[:,0]-=blend*shift[:,1]/math.tan(math.radians(-25))
    shift[:,1]*=1-blend
    main=np.clip((xy[:,1]-42)/1.0,0,1)
    shift*= (1-main*main*(3-2*main))[:,None]
    out=v.copy();out[:,:2]+=shift
    return out

reports={}
for part in ['road','terrain','earth_sides','guardrails']:
    tree,v,faces=read_mesh(SHAPES/f'{part}.dae')
    out=deform(v)
    mesh=tree.find('.//c:mesh',NS)
    pos_id=mesh.find('c:vertices/c:input',NS).get('source')[1:]
    sources={s.get('id'):s for s in mesh.findall('c:source',NS)}
    sources[pos_id].find('c:float_array',NS).text=' '.join(f'{x:.9g}' for x in out.ravel())
    # Transform existing smooth normals with the deformation Jacobian.
    # Replacing them with per-face normals would introduce visible faceting.
    vx=v.copy();vx[:,0]+=.0001
    vy=v.copy();vy[:,1]+=.0001
    jx=(deform(vx)-out)/.0001;jy=(deform(vy)-out)/.0001
    det=jx[:,0]*jy[:,1]-jy[:,0]*jx[:,1]
    accum={}
    for tri in mesh.findall('c:triangles',NS):
        inputs=tri.findall('c:input',NS); stride=max(int(i.get('offset')) for i in inputs)+1
        ix=np.fromstring(tri.find('c:p',NS).text,sep=' ',dtype=int).reshape(-1,3,stride)
        po=int(next(i for i in inputs if i.get('semantic')=='VERTEX').get('offset'))
        normal=next((i for i in inputs if i.get('semantic')=='NORMAL'),None)
        if normal is None:continue
        ni=normal.get('source')[1:];no=int(normal.get('offset'))
        original=np.fromstring(sources[ni].find('c:float_array',NS).text,sep=' ').reshape(-1,3)
        if ni not in accum:accum[ni]=np.zeros_like(original)
        for j in range(3):
            pi=ix[:,j,po];nn=original[ix[:,j,no]].copy();n=nn.copy()
            n[:,0]=(jy[pi,1]*nn[:,0]-jx[pi,1]*nn[:,1])/det[pi]
            n[:,1]=(-jy[pi,0]*nn[:,0]+jx[pi,0]*nn[:,1])/det[pi]
            n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-20)
            np.add.at(accum[ni],ix[:,j,no],n)
    for ni,n in accum.items():
        n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-20)
        sources[ni].find('c:float_array',NS).text=' '.join(f'{x:.9g}' for x in n.ravel())
    oldn=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]])
    newn=np.cross(out[faces[:,1]]-out[faces[:,0]],out[faces[:,2]]-out[faces[:,0]])
    flip=((oldn*newn).sum(1)<-1e-10)
    assert not flip.any(),f'{part}: flipped triangles {flip.sum()}'
    assert np.array_equal(out[:,2],v[:,2]),'elevation changed'
    tree.write(SHAPES/f'{part}_wide20.dae',encoding='utf-8',xml_declaration=True)
    reports[part]={'vertices':len(v),'triangles':len(faces),'maxShiftM':float(np.linalg.norm(out-v,axis=1).max()),'flippedTriangles':int(flip.sum())}

widths=[]
for seg in segments:
    if seg[0]!='line':continue
    _,a,b=seg;u=(b-a)/np.linalg.norm(b-a);n=np.array([-u[1],u[0]])
    c=a+.7*(b-a)
    vv=np.c_[np.stack([c-HALF*n,c+HALF*n]),np.zeros(2)]
    after=deform(vv)
    width=np.linalg.norm(after[1,:2]-after[0,:2]);assert abs(width-3.33)<1e-6
    widths.append(float(width))
reports['straightSlopeWidthsM']=widths
reports['mainRoadWidthM']=4
(ROOT/'widening_report.json').write_text(json.dumps(reports,indent=2))
prefab=ROOT/'package/art/hairpin_road/hairpin.prefab.json'
text=prefab.read_text()
for part in ['road','terrain','earth_sides','guardrails']:
    text=text.replace(f'/{part}.dae',f'/{part}_wide20.dae')
prefab.write_text(text)
print(json.dumps(reports))
