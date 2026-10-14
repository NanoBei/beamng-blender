"""Independently reopen the delivered blend and measure its actual world geometry."""
import bpy,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
D=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(D/'china_subject2_v07_final.blend'))
G=json.loads((D/'geometry_input.json').read_text());s=bpy.context.scene;bpy.context.view_layer.update()
report={'file':'china_subject2_v07_final.blend','checks':{},'failures':[]}
def points(obj):
    o=bpy.data.objects[obj] if isinstance(obj,str) else obj
    a=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',a);a=a.reshape(-1,3).astype(float)
    m=np.array(o.matrix_world);return a@m[:3,:3].T+m[:3,3]
def bounds(obj):
    a=points(obj);return a.min(0),a.max(0)
def check(name,actual,expected,tol=.001):
    err=float(np.max(np.abs(np.array(actual)-np.array(expected))));ok=err<=tol
    report['checks'][name]={'actual':np.asarray(actual).tolist(),'expected':np.asarray(expected).tolist(),'max_error':err,'tolerance':tol,'passed':ok}
    if not ok:report['failures'].append(name)
def require(name,ok,detail=None):
    report['checks'][name]={'passed':bool(ok),'detail':detail}
    if not ok:report['failures'].append(name)
def build_bvh(objects):
    vs=[];fs=[]
    for o in objects:
        off=len(vs);vs+=points(o).tolist();fs += [tuple(off+i for i in p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(vs,fs,all_triangles=False)
roads=[o for o in bpy.data.collections['01_Roads'].objects if o.name.startswith('ROAD_')]
bvh=build_bvh(roads)
def zhit(q):
    hit,normal,idx,distance=bvh.ray_cast(Vector((float(q[0]),float(q[1]),10)),Vector((0,0,-1)),20)
    return None if hit is None else hit.z
l,r,back=[bounds('LINE_Reverse_'+n) for n in ['Left','Right','Back']]
check('reverse_bay_width',r[0][0]-l[1][0],2.447)
check('reverse_bay_length',l[1][1]-back[1][1],5.558)
check('reverse_aisle_width',bounds('LINE_ReverseAisle_L')[0][1]-bounds('LINE_ReverseAisle_R')[1][1],7.287)
check('reverse_control_left',l[1][0]-bounds('LINE_Reverse_Control_Left')[1][0],7.287)
check('reverse_control_right',bounds('LINE_Reverse_Control_Right')[0][0]-r[0][0],7.287)
check('parallel_bay_length',bounds('LINE_Parallel_East')[0][0]-bounds('LINE_Parallel_West')[1][0],8.287)
check('parallel_bay_width',bounds('LINE_Parallel_Opening')[0][1]-bounds('LINE_Parallel_Back')[1][1],2.647)
check('parallel_lane_width',bounds('LINE_ParallelLane_L')[0][1]-bounds('LINE_ParallelLane_R')[1][1],3.5705)
check('right_angle_vertical_width',bounds('LINE_RightAngle_OuterEast')[0][0]-bounds('LINE_RightAngle_InnerWest')[1][0],3.908)
check('right_angle_horizontal_width',bounds('LINE_RightAngle_InnerNorth')[0][1]-bounds('LINE_RightAngle_OuterSouth')[1][1],3.908)
check('right_angle_outer_vertical_arm',bounds('LINE_RightAngle_OuterEast')[1][1]-bounds('LINE_RightAngle_OuterSouth')[1][1],10)
check('right_angle_outer_horizontal_arm',bounds('LINE_RightAngle_OuterEast')[0][0]-bounds('LINE_RightAngle_OuterSouth')[0][0],10)

def circle(name,expected_center,radius,sweep):
    p=points(name)[:,:2];near=np.linalg.norm(p-np.array(expected_center),axis=1)
    p=p[np.abs(near-radius)<.001]
    require(name+'_has_measured_inner_edge',len(p)>12,len(p))
    if len(p)<3:return
    fit=np.linalg.lstsq(np.c_[2*p,np.ones(len(p))],np.sum(p*p,axis=1),rcond=None)[0];c=fit[:2]
    radii=np.linalg.norm(p-c,axis=1)
    check(name+'_radius_extrema',[radii.min(),radii.max()],[radius,radius])
    angles=np.sort(np.mod(np.arctan2(p[:,1]-c[1],p[:,0]-c[0]),2*math.pi))
    span=2*math.pi-np.max(np.diff(np.r_[angles,angles[0]+2*math.pi]))
    check(name+'_angular_sweep',math.degrees(span),sweep,.002)
for i,curve in enumerate(['SCurve_First','SCurve_Second']):
    for side,radius in [('L',4 if i==0 else 7.5),('R',7.5 if i==0 else 4)]:
        circle('LINE_'+curve+'_'+side,G['validation_expected']['s_centers'][i],radius,135)
for side in ['L','R']:
    a=points('LINE_SCurve_First_'+side)[:,:2];b=points('LINE_SCurve_Second_'+side)[:,:2]
    distance=min(float(np.linalg.norm(x-b,axis=1).min()) for x in a)
    check('S_curve_tangent_paint_join_'+side,distance,0)
check('return_lane_width',bounds('LINE_西侧回程直道_L')[0][0]-bounds('LINE_西侧回程直道_R')[1][0],4.5)
# The inner paint intentionally opens where the main-road T junction meets the curve.
circle('LINE_回程上弯R10_R',[3,G['hill']['start'][1]-10],12.25,90)
circle('LINE_回程下弯R10_R',[3,20],12.25,90)

# Cross sections of real paint triangles, including triangulated main road boundaries.
def paint_intervals_x(x):
    intervals=[]
    for o in bpy.data.collections['02_Markings'].objects:
        if o.type!='MESH' or not o.name.startswith('LINE_'):continue
        p=points(o)
        if not (p[:,0].min()<=x<=p[:,0].max()):continue
        for face in o.data.polygons:
            q=p[list(face.vertices),:2];hit=[]
            for a,b in zip(q,np.roll(q,-1,axis=0)):
                if (a[0]-x)*(b[0]-x)<=0 and abs(b[0]-a[0])>1e-10:
                    t=(x-a[0])/(b[0]-a[0]);hit.append(float(a[1]+t*(b[1]-a[1])))
            if len(hit)>=2:intervals.append((min(hit),max(hit)))
    merged=[]
    for a,b in sorted(intervals):
        if merged and a<=merged[-1][1]+1e-5:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    return merged
main=[p for p in paint_intervals_x(25) if 40.7<p[0]<46.3]
require('main_road_two_boundary_lines',len(main)==2,main)
if len(main)==2:check('main_road_net_width',main[1][0]-main[0][1],5)
hp=next(p for p in G['net_footprints'] if p['name']=='原V20双发卡弯')
source_samples=np.array(hp['xy'])[::10]
source_support=[zhit(p) for p in source_samples]
require('imported_hairpin_boundary_supported_flat',all(z is not None and abs(z)<.001 for z in source_support))
for o in roads:
    if 'Flat' in o.name:check(o.name+'_all_vertices_flat',np.max(np.abs(points(o)[:,2])),0,1e-6)

p=points('ROAD_HillRamp')[::2];xs=p[:,0];zs=p[:,2];order=np.argsort(xs);xs=xs[order];zs=zs[order]
check('hill_horizontal_length',xs.max()-xs.min(),G['hill']['total'])
check('hill_peak',zs.max(),G['hill']['height'])
check('hill_ground_joins',[zs[0],zs[-1]],[0,0])
check('hill_net_width',bounds('LINE_HillRamp_R')[0][1]-bounds('LINE_HillRamp_L')[1][1],3.5)
dx=np.diff(xs);dz=np.diff(zs);station=xs.max()-xs
mask=(station[:-1]>3.1)&(station[1:]<22.8)&(dx>1e-5)
grade=dz[mask]/dx[mask]
check('hill_constant_grade_extrema',[grade.min(),grade.max()],[-.1,-.1],.0003)
slopes=dz[dx>1e-5]/dx[dx>1e-5]
require('hill_vertical_transition_continuity',np.max(np.abs(np.diff(slopes)))<.003,{'max_grade_change':float(np.max(np.abs(np.diff(slopes))))})
centres={n:sum(v[0] for v in bounds('LINE_Ramp_'+n))/2 for n in ['Before','Stop','After']}
check('hill_stop_station',xs.max()-centres['Stop'],12)
check('hill_control_line_spacing',[centres['Before']-centres['Stop'],centres['Stop']-centres['After']],[.65,.65])

# Measure saved road triangle area and compare with the independently prepared union.
area=0;bad_normals=[]
for o in roads:
    a=points(o)
    for poly in o.data.polygons:
        q=a[list(poly.vertices)]
        for i in range(1,len(q)-1):
            a1=q[i,:2]-q[0,:2];a2=q[i+1,:2]-q[0,:2];area+=abs(float(a1[0]*a2[1]-a1[1]*a2[0]))/2
        if poly.area>1e-9 and poly.normal.z<.5:bad_normals.append(o.name);break
check('saved_pavement_projected_area',area,G['geometry_preparation']['pavement_union_area_m2'],.005)
require('road_top_normals_up',not bad_normals,bad_normals)
unsupported=[];lifts=[]
for o in bpy.data.collections['02_Markings'].objects:
    if o.type!='MESH':continue
    p=points(o)
    for a in p[::max(1,len(p)//250)]:
        z=zhit(a)
        if z is None:unsupported.append(o.name);break
        lifts.append(float(a[2]-z))
require('all_paint_supported_by_road',not unsupported,unsupported)
require('paint_surface_lift',min(lifts)>-.0001 and max(lifts)<.004,{'min':min(lifts),'max':max(lifts)})
# Sample the entire centreline loop after reopening, plus both boundaries of the hill ends.
route_gaps=[]
for rr in G['routes']:
    for row in rr['rows'][::max(1,len(rr['rows'])//100)]:
        z=zhit(row)
        if z is None:route_gaps.append(rr['name'])
require('loop_and_branch_surfaces_continuous',not route_gaps,sorted(set(route_gaps)))
# Physical facilities must be outside the net driving areas.
vs=[];fs=[]
for pp in G['net_footprints']:
    coords=[Vector((x,y,0)) for x,y in pp['xy']]
    from mathutils.geometry import tessellate_polygon
    tris=tessellate_polygon([coords]);lookup={tuple(p):i for i,p in enumerate(coords)};off=len(vs);vs.extend(coords)
    for t in tris:fs.append(tuple(off+(i if isinstance(i,int) else lookup[tuple(i)]) for i in t))
net_bvh=BVHTree.FromPolygons(vs,fs,all_triangles=True)
intrusions=[]
for o in bpy.data.collections['03_Facilities'].objects:
    if o.name.startswith(('DRAIN_Frame','SIGN_Post')):
        for q in points(o):
            hit,*_=net_bvh.ray_cast(Vector((q[0],q[1],5)),Vector((0,0,-1)),10)
            if hit is not None:intrusions.append(o.name);break
cp=points('CURBS_BlackYellow').reshape(-1,8,3).mean(1)
for q in cp:
    hit,*_=net_bvh.ray_cast(Vector((q[0],q[1],5)),Vector((0,0,-1)),10)
    if hit is not None:intrusions.append('CURBS_BlackYellow');break
require('facilities_outside_net_driving_width',not intrusions,intrusions)

high=bpy.data.collections['05_ReferenceCar_HIGH'];proxy=bpy.data.collections['06_ReferenceCar_PROXY']
require('car_display_switch',proxy.hide_render and not high.hide_render and all(o.hide_get() for o in high.objects if o.type=='MESH'))
root=next(o for o in high.objects if o.type=='EMPTY')
for o in high.objects:o.hide_set(False)
bpy.context.view_layer.update();inv=np.array(root.matrix_world.inverted());lo=np.full(3,np.inf);hi=-lo;blo=np.inf;bhi=-np.inf;wheels=[]
for o in high.objects:
    if o.type!='MESH':continue
    w=points(o);p=w@inv[:3,:3].T+inv[:3,3];lo=np.minimum(lo,p.min(0));hi=np.maximum(hi,p.max(0))
    attr=o.data.attributes.get('exclude_from_body_width')
    if attr:
        values=np.empty(len(p),dtype=bool);attr.data.foreach_get('value',values);bp=p[~values]
    else:bp=p
    if len(bp):blo=min(blo,bp[:,1].min());bhi=max(bhi,bp[:,1].max())
    if o.get('axle'):
        mid=(p.min(0)+p.max(0))/2;wm=(w.min(0)+w.max(0))/2
        wheels.append(dict(axle=o['axle'],x=mid[0],bottom=float(w[:,2].min()),road_z=zhit(wm)))
check('C63_length_bodywidth_mirrorwidth_height',[hi[0]-lo[0],bhi-blo,hi[1]-lo[1],hi[2]-lo[2]],[4.756,1.839,2.020,1.426])
check('C63_wheelbase',np.mean([w['x'] for w in wheels if w['axle']=='front'])-np.mean([w['x'] for w in wheels if w['axle']=='rear']),2.840)
require('C63_four_wheels_supported',len(wheels)==4 and all(w['road_z'] is not None and abs(w['bottom']-w['road_z'])<.001 for w in wheels),wheels)
count=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in proxy.objects if o.type=='MESH')
require('C63_proxy_under_300k',count<=300000,count)
require('car_shared_parent',all(o.parent==root for o in proxy.objects if o.type=='MESH'))
missing=[im.filepath for im in bpy.data.images if im.users and im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file()]
require('no_missing_used_textures',not missing,missing)
fonts=[f.filepath for f in bpy.data.fonts if f.users and f.filepath and f.filepath!='<builtin>' and not f.packed_file and not Path(bpy.path.abspath(f.filepath)).is_file()]
require('no_missing_used_fonts',not fonts,fonts)
check('site_size',np.subtract(*reversed(bounds('LAND_Site90x60')))[:2],[90,60])
require('metre_units',s.unit_settings.system=='METRIC' and s.unit_settings.scale_length==1)
report['passed']=not report['failures']
(D/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'failures':report['failures']},ensure_ascii=False),flush=True)
if report['failures']:raise RuntimeError('Saved-scene checks failed: '+str(report['failures']))
