"""Compile the approved V07 plan into non-overlapping pavement and editable decals.
Run with the bundled Python 3.12; Shapely lives in this directory's .deps only.
No Blender operations occur here. geometry_input.json is the Blender build input.
"""
from pathlib import Path
import ast, json, math, sys, hashlib, random
import numpy as np
D=Path(__file__).resolve().parent;ROOT=D.parent
sys.path.insert(0,str(D/'.deps'))
import shapely
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles,orient_polygons,make_valid
plan=ROOT/'layout_proposal_v07/make_plan.py'
tree=ast.parse(plan.read_text());cut=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='project_polys' for t in n.targets))
tree.body=tree.body[:cut];ns={'__file__':str(plan)};exec(compile(tree,str(plan),'exec'),ns)
P=json.loads((ROOT/'parameters.json').read_text());q=P['design_defaults'];dim=P['dimensions']
pad=q['line_width']+q['shoulder_beyond_paint'];lw=q['line_width'];lift=q['paint_lift']
site=box(-10,0,80,60);rows=ns['routes'];sf=ns['surfaces']
polys={s['name']:make_valid(Polygon(s['poly'])) for s in sf}
net=unary_union(list(polys.values()))
paved=net.buffer(pad,join_style='mitre').intersection(site)
hs=ns['hill_start'];he=ns['hill_end'];up=ns['up'];total=ns['hill_total'];peak=ns['hill_h'];run=ns['run'];rise=ns['rise']
hill=box(he[0],hs[1]-1.75-pad,hs[0],hs[1]+1.75+pad)
flat=paved.difference(hill)
concrete_names=[s['name'] for s in sf if s['kind']=='exam' or s['name'] in ['原V20双发卡弯','发卡末端平面连接弯R10','发卡回接大路']]
concrete=unary_union([polys[n].buffer(pad,join_style='mitre') for n in concrete_names]).intersection(flat)
asphalt=flat.difference(concrete)
def parts(g):
    if g.is_empty:return []
    if g.geom_type=='Polygon':return [g]
    if not hasattr(g,'geoms'):return []
    return [p for sub in g.geoms for p in parts(sub)]
def ascent(s):
    if s<=run:return 30-math.sqrt(max(0,900-s*s))
    if s<=run+20:return rise+(s-run)*.1
    v=up-s;return peak-(30-math.sqrt(max(0,900-v*v)))
def height(x,y):
    s=float(hs[0]-x)
    if abs(y-hs[1])>2.7 or s<=0 or s>=total:return 0.
    if s<up:return ascent(s)
    if s<=up+6:return peak
    return ascent(total-s)
def meshdata(g,z=0,follow=False):
    verts=[];faces=[];lookup={}
    for poly in parts(make_valid(g)):
        for tri in constrained_delaunay_triangles(poly).geoms:
            coords=list(tri.exterior.coords)[:3]
            if (coords[1][0]-coords[0][0])*(coords[2][1]-coords[0][1])-(coords[1][1]-coords[0][1])*(coords[2][0]-coords[0][0])<0:coords.reverse()
            face=[]
            for x,y in coords:
                key=(round(x,9),round(y,9));idx=lookup.get(key)
                if idx is None:
                    idx=len(verts);lookup[key]=idx;verts.append([x,y,z+(height(x,y) if follow else 0)])
                face.append(idx)
            faces.append(face)
    return dict(vertices=verts,faces=faces)
out={'schema':1,'approved_plan':'layout_proposal_v07','approved_plan_sha256':hashlib.sha256((ROOT/'layout_proposal_v07/layout_parameters.json').read_bytes()).hexdigest(),
     'units':'metres; Z up','parameters':P,'site_bounds':[[-10,0],[80,60]],'source':ns['source_records'],
     'hill':dict(start=hs.tolist(),end=he.tolist(),up=up,total=total,height=peak,run=run,rise=rise),
     'roads':[],'markings':[],'curbs':[],'details':[],'vegetation':[],
     'routes':[dict(name=r['name'],kind=r['kind'],rows=r['rows'].tolist()) for r in rows],
     'net_footprints':[{**{'name':s['name'],'kind':s['kind']},'xy':s['poly'].tolist()} for s in sf]}
for name,geom,mat in [('ROAD_Flat_Concrete',concrete,'concrete'),('ROAD_Flat_Asphalt',asphalt,'asphalt')]:
    out['roads'].append(dict(name=name,material=mat,**meshdata(geom)))
stations=set(np.linspace(0,total,math.ceil(total/.06)+1));stations.update([0,run,run+20,up,up+6,total-run-20,total-run,total])
for v in [-.65,0,.65]:
    w=.30 if v==0 else lw;stations.update([12+v-w/2,12+v,12+v+w/2])
stations=sorted(stations);v=[]
for s in stations:
    for yy in [hs[1]-1.75-pad,hs[1]+1.75+pad]:v.append([hs[0]-s,yy,height(hs[0]-s,yy)])
out['roads'].append(dict(name='ROAD_HillRamp',material='concrete',vertices=v,faces=[[i*2,i*2+1,i*2+3,i*2+2] for i in range(len(stations)-1)]))

# Paint occupies the shoulder outside the clear envelope. Shared junctions stay open.
paint=net.buffer(lw,join_style='mitre').difference(net).intersection(paved).difference(box(-10.1,27.74,-9.995,32.26))
paint_left=paint
def mark(name,g,mat='white',clip=True):
    global paint_left
    g=make_valid(g)
    if clip:
        g=g.intersection(paint_left);paint_left=paint_left.difference(g)
    if g.is_empty:return
    # Intersect ramp decals with the same station strips, avoiding bowed long triangles.
    outside=g.difference(hill)
    data=meshdata(outside,z=lift)
    gh=g.intersection(hill)
    if not gh.is_empty:
        for a,b in zip(stations,stations[1:]):
            piece=gh.intersection(box(hs[0]-b,hs[1]-2.3,hs[0]-a,hs[1]+2.3))
            dd=meshdata(piece,z=lift,follow=True);off=len(data['vertices']);data['vertices']+=dd['vertices'];data['faces'] += [[i+off for i in f] for f in dd['faces']]
    if data['faces']:out['markings'].append(dict(name=name,material=mat,**data))
bx=ns['bx'];ry=ns['ry'];by=ns['by'];rv=ns['rv'];pv=ns['pv'];px0=ns['px0'];px1=ns['px1'];py=ns['py'];back=ry-rv['length']
for name,g in [('Reverse_Left',box(bx-lw,back-lw,bx,ry)),('Reverse_Right',box(bx+rv['width'],back-lw,bx+rv['width']+lw,ry)),('Reverse_Back',box(bx,back-lw,bx+rv['width'],back)),
               ('Parallel_West',box(px0-lw,py-pv['width']-lw,px0,py)),('Parallel_East',box(px1,py-pv['width']-lw,px1+lw,py)),('Parallel_Back',box(px0,py-pv['width']-lw,px1,py-pv['width']))]:mark('LINE_'+name,g)
cx,cy=ns['corner'];cw=ns['cw'];ex=ns['ex'];ey=ns['ey'];east=cx+cw/2;south=cy-cw/2;ix=cx-cw/2;iy=cy+cw/2
for name,g in [('OuterEast',box(east,south,east+lw,ey)),('OuterSouth',box(ex,south-lw,east+lw,south)),('InnerWest',box(ix-lw,iy,ix,ey)),('InnerNorth',box(ex,iy,ix,iy+lw))]:mark('LINE_RightAngle_'+name,g)
names={'01倒库车道':'ReverseAisle','02侧方车道':'ParallelLane','03S弯第一段':'SCurve_First','03S弯第二段':'SCurve_Second','05坡道':'HillRamp'}
for rr in rows:
    a=rr['rows'];n=np.column_stack([-np.sin(a[:,2]),np.cos(a[:,2])])
    for sign in [-1,1]:
        inside=a[:,:2]+sign*n*a[:,3:4]/2;outside=a[:,:2]+sign*n*(a[:,3:4]/2+lw)
        shape=Polygon(np.vstack([inside,outside[::-1]]))
        name='LINE_'+names.get(rr['name'],'Route_'+str(rows.index(rr)) if False else rr['name'])+('_L' if sign==1 else '_R')
        mark(name,shape)
mark('LINE_FlatRoad_OuterBoundaries',paint_left)
def dash(name,a,b,width=lw):
    a=np.array(a);b=np.array(b);u=(b-a)/np.linalg.norm(b-a);n=np.array([-u[1],u[0]])*width/2
    ll=np.linalg.norm(b-a);pol=[]
    for s in np.arange(0,ll,2):
        aa=a+u*s;bb=a+u*min(s+1,ll);pol.append(Polygon([aa-n,bb-n,bb+n,aa+n]))
    mark(name,unary_union(pol),'white',False)
dash('LINE_Reverse_Opening',(bx,ry+lw/2),(bx+rv['width'],ry+lw/2))
dash('LINE_Parallel_Opening',(px0,py+lw/2),(px1,py+lw/2))
dash('LINE_Reverse_Control_Left',(ns['rx0']-lw/2,ry),(ns['rx0']-lw/2,by+rv['aisle_width']/2))
dash('LINE_Reverse_Control_Right',(ns['rx1']+lw/2,ry),(ns['rx1']+lw/2,by+rv['aisle_width']/2))
for name,off in [('Before',-.65),('Stop',0),('After',.65)]:
    x=hs[0]-12-off;w=.30 if not off else lw
    mark('LINE_Ramp_'+name,box(x-w/2,hs[1]-1.75,x+w/2,hs[1]+1.75),'yellow',False)
def arrow(name,x,y,h,length=1):
    coords=[(-1,-.14),(.3,-.14),(.3,-.43),(1,0),(.3,.43),(.3,.14),(-1,.14)]
    g=Polygon([(x+length*(a*math.cos(h)-b*math.sin(h)),y+length*(a*math.sin(h)+b*math.cos(h))) for a,b in coords])
    assert net.buffer(.001).covers(g),name
    mark(name,g,'white',False)
for i,(x,y,h) in enumerate([(8.5,10,0),(26.5,10,0),(43,10,0),(-7,25,-math.pi/2),(-7,37,-math.pi/2),
    (62,ns['cy'],0),(ns['cx'],40,math.pi/2),(42,hs[1],math.pi),(17,hs[1],math.pi),
    (0,43.5,0),(50,43.5,0),(ns['re'][0],34,math.pi/2)]):arrow('ARROW_'+str(i),x,y,h)
for ii,rr in enumerate([ns['s1'],ns['s2'],ns['loop_top'],ns['loop_bottom']]):
    p=rr[len(rr)//2];arrow('ARROW_Curve_'+str(ii),p[0],p[1],p[2],.8)

# Follow only the outside of the unified pavement, including greenery islands.
for pp in parts(orient_polygons(paved)):
    for ring in [pp.exterior,*pp.interiors]:
        line=LineString(ring.coords);N=math.ceil(line.length/.5)
        for i in range(N):
            aa=np.array(line.interpolate(i*line.length/N).coords[0]);bb=np.array(line.interpolate((i+1)*line.length/N).coords[0]);mid=(aa+bb)/2
            if mid[0]<-9.99:continue
            direction=bb-aa;length=np.linalg.norm(direction)
            if length<1e-6:continue
            normal=np.array([direction[1],-direction[0]])/length*.18
            corners=[aa,bb,bb+normal,aa+normal]
            out['curbs'].append(dict(xy=[a.tolist() for a in corners],z=[height(*a) for a in corners],material=i%2))

# Realistic detailing in editable layers, with deterministic placement.
random.seed(1248)
for rr in rows:
    if rr['kind'] not in ['exam','hill','flat_connector']:continue
    if rr['name']=='原大路延伸接科目二连接道' or rr['name']=='原大路西端接回程道':continue
    a=rr['rows'];dist=0;last=-1
    for j in range(1,len(a)):
        dist+=np.linalg.norm(a[j,:2]-a[j-1,:2])
        if dist-last<4:continue
        x,y,h,w=a[j];n=np.array([-math.sin(h),math.cos(h)]);pol=LineString([np.array([x,y])-n*(w/2+pad-.04),np.array([x,y])+n*(w/2+pad-.04)]).buffer(.006,cap_style='flat')
        mark('DETAIL_Joint_'+rr['name']+'_'+str(j),pol.intersection(paved),'joint',False);last=dist
for xx,yy in [(20,11.2),(35,10.7),(16,35),(27,26),(38,18.4),(69,32)]:
    line=LineString([(xx+i*.14,yy+random.uniform(-.08,.08)) for i in range(8)]).buffer(.004,cap_style='flat')
    if paved.covers(line):mark('DETAIL_Crack_'+str(xx),line,'joint',False)
for name,poly in [('Reverse',box(18.3,8.1,19.9,9.3)),('Parallel',box(40,10.4,41.4,11.1))]:
    mark('DETAIL_Repair_'+name,poly.intersection(net),'repair',False)
# Intermittent tyre traces, not instructional racing lines.
for ri,arr in enumerate([ns['s1'],ns['s2'],ns['hp_rows']]):
    for start in range(30,len(arr)-35,110):
        for offset in [-.72,.72]:
            qs=arr[start:start+22];xy=qs[:,:2]+offset*np.column_stack([-np.sin(qs[:,2]),np.cos(qs[:,2])])
            trace=LineString(xy).buffer(.025,cap_style='flat').intersection(net)
            mark(f'DETAIL_Tyre_{ri}_{start}_{offset}',trace,'tire',False)
land_clear=site.buffer(-2).difference(paved.buffer(3))
for y in range(5,58,7):
    for x in range(-2,78,8):
        xx=x+random.uniform(-1,1);yy=y+random.uniform(-1,1)
        if land_clear.covers(Point(xx,yy)) and random.random()<.58:out['vegetation'].append([xx,yy,random.uniform(.75,1.05)])
out['grass_points']=[]
grass_exclusion=paved.buffer(.30)
for i in range(5500):
    x=random.uniform(-9.5,79.5);y=random.uniform(.5,59.5)
    if not grass_exclusion.covers(Point(x,y)):out['grass_points'].append([x,y,random.uniform(.055,.14)])
out['validation_expected']=dict(reverse=[bx,bx+rv['width'],back,ry],parallel=[px0,px1,py-pv['width'],py],
    right_angle=ns['ra'].tolist(),s_centers=[(ns['s1'][0,:2]+np.array([0,5.75])).tolist(),
        (ns['s2'][0,:2]-5.75*np.array([-math.sin(ns['s2'][0,2]),math.cos(ns['s2'][0,2])])).tolist()],
    paved_area_m2=paved.area,flat_area_m2=flat.area,net_area_m2=net.area,curb_blocks=len(out['curbs']))
areas=sum(sum(Polygon([r['vertices'][i][:2] for i in f]).area for f in r['faces']) for r in out['roads'])
assert abs(areas-paved.area)<1e-6,(areas,paved.area)
assert concrete.intersection(asphalt).area<1e-9
out['geometry_preparation']=dict(shapely=shapely.__version__,pavement_union_area_m2=paved.area,
    triangulated_area_m2=areas,flat_material_overlap_m2=concrete.intersection(asphalt).area,
    plan_geometry_unchanged=True,project_count=5)
(D/'geometry_input.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
(D/'parameters_v07.json').write_text(json.dumps(dict(approved=True,baseline=P,layout=json.loads((ROOT/'layout_proposal_v07/layout_parameters.json').read_text()),
     model_decisions=dict(flat_hairpin_z=0,flat_main_road_z=0,exam_ramp_grade=.1,roadside_pad=pad,curb_width=.18,curb_height=.15)),ensure_ascii=False,indent=2))
print(json.dumps({'roads':len(out['roads']),'markings_and_detail_meshes':len(out['markings']),'curbs':len(out['curbs']),'trees':len(out['vegetation']),'area':areas},ensure_ascii=False))
