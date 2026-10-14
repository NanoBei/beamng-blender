"""Build the approved course in an isolated Blender process. No live MCP edits.
Run: Blender --background --factory-startup --disable-autoexec --python build_scene.py
"""
import bpy, math, json, random, os, sys
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'parameters.json').read_text()); D=P['dimensions']; Q=P['design_defaults']
random.seed(Q['random_seed'])
scene=bpy.context.scene
# Only the factory scene of this dedicated process is cleared.
assert not bpy.data.filepath, 'Run with --factory-startup, never on an existing file'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene.name='C1_Subject2_100x75m'; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
C={}
for name in ['01_Roads','02_Markings','03_Facilities','04_Landscape','05_ReferenceCar_HIGH','06_ReferenceCar_PROXY','07_Dimensions','08_Presentation']:
    c=bpy.data.collections.new(name); scene.collection.children.link(c); C[name[3:]]=c

def mesh(name,vs,fs,mat=None,col='Roads'):
    m=bpy.data.meshes.new(name); m.from_pydata(vs,[],fs); m.update()
    o=bpy.data.objects.new(name,m); C[col].objects.link(o)
    if mat:o.data.materials.append(mat)
    return o

def move_collection(o,col):
    for c in list(o.users_collection):c.objects.unlink(o)
    C[col].objects.link(o)

def box(name,center,size,mat,col='Facilities',bevel=0):
    x,y,z=center; a,b,c=(s/2 for s in size)
    vs=[(x+dx*a,y+dy*b,z+dz*c) for dx,dy,dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,col)
    if bevel:
        mod=o.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel;mod.segments=2
    return o

def rect(name,x1,x2,y1,y2,z,mat,col='Markings'):
    return mesh(name,[(x1,y1,z),(x2,y1,z),(x2,y2,z),(x1,y2,z)],[(0,1,2,3)],mat,col)

def polygon(name,coords,z,mat,col='Roads',thick=0):
    pts=[Vector((x,y,z)) for x,y in coords]; ts=tessellate_polygon([pts])
    idx={tuple(v):i for i,v in enumerate(pts)}
    faces=[tuple(v if isinstance(v,int) else idx[tuple(v)] for v in t) for t in ts]
    vs=[tuple(v) for v in pts]
    if thick:
        n=len(vs);vs += [(x,y,z-thick) for x,y in coords]
        faces += [tuple(i+n for i in reversed(f)) for f in faces[:]]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vs,faces,mat,col)

def mat_simple(name,color,rough=.7,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    return m

def weathered(name,color,rough=.85,grain=160,bump=.0015):
    m=mat_simple(name,color,rough); n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    geo=n.new('ShaderNodeNewGeometry'); low=n.new('ShaderNodeTexNoise');low.inputs['Scale'].default_value=.65;low.inputs['Detail'].default_value=3
    l.new(geo.outputs['Position'],low.inputs['Vector']);r=n.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position=.15;r.color_ramp.elements[0].color=tuple(c*.73 for c in color)+(1,)
    r.color_ramp.elements[1].position=.85;r.color_ramp.elements[1].color=tuple(min(1,c*1.14) for c in color)+(1,)
    l.new(low.outputs['Fac'],r.inputs[0]);l.new(r.outputs['Color'],bs.inputs['Base Color'])
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=grain;fine.inputs['Detail'].default_value=2
    l.new(geo.outputs['Position'],fine.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.32;b.inputs['Distance'].default_value=bump
    l.new(fine.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],bs.inputs['Normal'])
    return m

concrete=weathered('C1_Weathered_light_concrete',(.36,.385,.38),grain=230,bump=.0018)
asphalt=weathered('C1_Connector_asphalt',(.105,.123,.13),grain=300,bump=.0025)
white=weathered('C1_Offwhite_road_paint',(.79,.8,.72),.72,grain=110,bump=.0003)
yellow=weathered('C1_Safety_yellow',(.78,.48,.035),.7,grain=80,bump=.0004)
black=weathered('C1_Curb_charcoal',(.023,.029,.03),grain=120)
soil=weathered('C1_Dry_soil',(.15,.125,.075),grain=140,bump=.008)
grass=weathered('C1_Grass_ground',(.12,.18,.07),grain=90,bump=.015)
joint=mat_simple('C1_Expansion_joint',(.065,.074,.07),.96)
metal=mat_simple('C1_Galvanised_steel',(.30,.34,.36),.38,.75)
blue=mat_simple('C1_Sign_blue',(.018,.10,.19),.42)
cream=weathered('C1_Rendered_masonry',(.49,.47,.40),grain=70)
glass=mat_simple('C1_Window',(.07,.14,.17),.18,.35)
wood=weathered('C1_Tree_bark',(.10,.064,.031),grain=32,bump=.015)
leaves=[weathered('C1_Leaves_'+str(i),c,grain=30,bump=.006) for i,c in enumerate([(.10,.22,.055),(.16,.25,.07),(.07,.155,.045)])]
patchmat=weathered('C1_Concrete_repairs',(.285,.30,.29),grain=200)
tiremat=mat_simple('C1_Subtle_rubber_scuffs',(.17,.19,.18),.98)

# Station = x,y,z,heading,width. Every join uses the same cross section.
segments=[];samples=[]
def add(name,pts,material=asphalt,exam=None):
    segments.append(dict(name=name,points=pts,material=material,exam=exam));samples.extend(pts)
    return pts[-1]
def straight(name,start,end,width0=4.5,width1=None,material=asphalt,step=.25,exam=None):
    if width1 is None:width1=width0
    x,y=start[:2];ex,ey=end[:2];length=math.hypot(ex-x,ey-y);h=math.atan2(ey-y,ex-x);n=max(1,math.ceil(length/step))
    return add(name,[(x+(ex-x)*i/n,y+(ey-y)*i/n,0,h,width0+(width1-width0)*i/n) for i in range(n+1)],material,exam)
def arc(name,start,heading,delta,r=10,width=4.5,material=asphalt,exam=None):
    sign=1 if delta>0 else -1; cx=start[0]-sign*r*math.sin(heading);cy=start[1]+sign*r*math.cos(heading)
    n=max(1,math.ceil(abs(delta)*r/.08));pts=[]
    for i in range(n+1):
        a=heading+delta*i/n;pts.append((cx+sign*r*math.sin(a),cy-sign*r*math.cos(a),0,a,width))
    end=add(name,pts,material,exam)
    segments[-1]['circle_center']=[cx,cy];return end

rw=D['reverse']['aisle_width'];pw=D['parallel']['lane_width'];lw=Q['line_width'];pad=lw+Q['shoulder_beyond_paint'];lift=Q['paint_lift']
straight('Entrance',(0,16),(2,16));straight('ReverseEntryTaper',(2,16),(5,16),4.5,rw)
straight('ReverseAisle',(5,16),(25,16),rw,material=concrete,exam='reverse')
straight('ReverseExitTaper',(25,16),(29,16),rw,4.5)
a=arc('Connector01',(29,16),0,math.pi/2)
straight('Connector02',a,(39,34));a=arc('Connector03',(39,34),math.pi/2,math.pi/2)
straight('ParallelEntryTaper',a,(27,44),4.5,pw)
straight('ParallelLane',(27,44),(15,44),pw,material=concrete,exam='parallel')
# Width returns to 4.5 along the beginning of the western connector.
a=arc('Connector04',(15,44),math.pi,-math.pi/2,width=4.5)
segments[-1]['points']=[(*p[:4],pw+(4.5-pw)*min(i/40,1)) for i,p in enumerate(segments[-1]['points'])]
straight('Connector05',a,(5,55));a=arc('Connector06',(5,55),math.pi/2,-math.pi/2)
straight('RampEntryTaper',a,(26,65),4.5,3.5)
R=Q['ramp_vertical_radius']; grade=D['ramp']['grade'];ang=math.atan(grade);run=R*math.sin(ang);rise=R*(1-math.cos(ang));glen=Q['ramp_constant_grade_horizontal'];up=2*run+glen;peak=2*rise+grade*glen;plat=Q['ramp_platform_length'];total=2*up+plat

def ascent(s):
    if s<=run:return R-math.sqrt(max(0,R*R-s*s))
    if s<=run+glen:return rise+(s-run)*grade
    q=up-s;return peak-(R-math.sqrt(max(0,R*R-q*q)))
def ramp_z(s):
    if s<=0 or s>=total:return 0
    if s<up:return ascent(s)
    if s<=up+plat:return peak
    return ascent(total-s)
# Include every analytic transition and stopline edge exactly.
stations=set([0,run,run+glen,up,up+plat,total-run-glen,total-run,total])
stations.update(total*i/math.ceil(total/.08) for i in range(math.ceil(total/.08)+1))
for k in [-.65,0,.65]:
    width=Q['ramp_stop_line_width'] if k==0 else lw
    stations.update([12+k-width/2,12+k,12+k+width/2])
add('HillRamp',[(26+s,65,ramp_z(s),0,3.5) for s in sorted(stations)],concrete,'ramp')
ramp_end=26+total
a=arc('Connector07',(ramp_end,65),0,-math.pi/2,width=3.5)
segments[-1]['points']=[(*p[:4],3.5+(4.5-3.5)*min(i/40,1)) for i,p in enumerate(segments[-1]['points'])]
straight('SCurveApproach',a,(a[0],45),4.5,3.5)
sstart=(a[0],45);cr=(D['s_curve']['outer_radius']+D['s_curve']['inner_radius'])/2
s1=arc('SCurve_First',sstart,-math.pi/2,-math.radians(135),cr,3.5,concrete,'s_curve')
s2=arc('SCurve_Second',s1,s1[3],math.radians(135),cr,3.5,concrete,'s_curve')
aw=D['right_angle']['width'];straight('RightAngleApproach',s2,(s2[0],27),3.5,aw)
ax=s2[0];east=ax+aw/2;west=east-Q['right_angle_outer_arm'];north=27;south=north-Q['right_angle_outer_arm'];exit_y=south+aw/2
# Exact right angle union of two rectangular arms, no rounded corner.
inner_x=east-aw;inner_y=south+aw
right_coords=[(west,south),(east,south),(east,north),(inner_x,north),(inner_x,inner_y),(west,inner_y)]
outer_coords=[(west,south-pad),(east+pad,south-pad),(east+pad,north),(inner_x-pad,north),(inner_x-pad,inner_y+pad),(west,inner_y+pad)]
straight('RightAngleExit',(west,exit_y),(57,exit_y),aw,4.5)
straight('ExitStraight',(57,exit_y),(50,exit_y))
a=arc('ExitBend',(50,exit_y),math.pi,math.pi/2)
straight('Exit',a,(40,0))

# Road profiles and flat parking-bay extensions.
def road_segment(seg):
    pts=seg['points'];vs=[]
    for x,y,z,h,w in pts:
        nx,ny=-math.sin(h),math.cos(h)
        for k in [-1,1]:vs.append((x+k*(w/2+pad)*nx,y+k*(w/2+pad)*ny,z))
    faces=[(2*i,2*i+2,2*i+3,2*i+1) for i in range(len(pts)-1)]
    o=mesh('ROAD_'+seg['name'],vs,faces,seg['material']);o['section']=seg.get('exam') or 'connector'
    # Side walls only; road top remains analytically measurable.
    wallvs=[];wallfs=[]
    for side in [0,1]:
        for i in range(len(pts)-1):
            a=vs[2*i+side];b=vs[2*(i+1)+side];j=len(wallvs)
            wallvs.extend([a,b,(b[0],b[1],-.18),(a[0],a[1],-.18)]);wallfs.append((j,j+1,j+2,j+3))
    mesh('BED_'+seg['name'],wallvs,wallfs,concrete)
    if seg.get('circle_center'):o['circle_center']=seg['circle_center']
    return o
for seg in segments:road_segment(seg)
polygon('ROAD_RightAngle',outer_coords,0,concrete,thick=.18)
rx0=Q['reverse_control_left_x']+D['reverse']['control_each_side'];rx1=rx0+D['reverse']['width'];rfront=16-rw/2;rback=rfront-D['reverse']['length']
box('ROAD_ReverseBay',((rx0+rx1)/2,(rback-pad+rfront-pad)/2,-.09),(rx1-rx0+2*pad,rfront-rback,.18),concrete,'Roads')
px0=Q['parallel_bay_west_x'];px1=px0+D['parallel']['length'];popen=44+pw/2;pback=popen+D['parallel']['width']
box('ROAD_ParallelBay',((px0+px1)/2,(popen+pad+pback+pad)/2,-.09),(px1-px0+2*pad,pback-popen,.18),concrete,'Roads')
box('LAND_Site100x75',(50,37.5,-.19),(100,75,.33),grass,'Landscape',.12)

# Boundary paint strips and segmented yellow/black kerbs.
curbverts=[];curbfaces=[];curbmats=[]
def opening(seg,p,side,curb=False):
    x,y=p[:2];margin=pad+.02 if curb else 0
    return ((seg['name']=='ReverseAisle' and side==-1 and rx0-margin<x<rx1+margin) or
            (seg['name']=='ParallelLane' and side==-1 and px0-margin<x<px1+margin))
def add_curb(a,b,index):
    # a/b are inner edge endpoints. Top follows the local grade.
    x,y,z=a;ex,ey,ez=b;dx,dy=ex-x,ey-y;length=math.hypot(dx,dy)
    if length<1e-6:return
    nx,ny=-dy/length,dx/length;w=Q['curb_width'];h=Q['curb_height'];j=len(curbverts)
    curbverts.extend([(x,y,z),(ex,ey,ez),(ex+nx*w,ey+ny*w,ez),(x+nx*w,y+ny*w,z),
        (x,y,z+h),(ex,ey,ez+h),(ex+nx*w,ey+ny*w,ez+h),(x+nx*w,y+ny*w,z+h)])
    fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    curbfaces.extend([tuple(j+k for k in f) for f in fs]);curbmats.extend([index%2]*6)

def strip_path(name,pts,side,inner,outer,mat=white,skip=None,col='Markings'):
    vs=[];fs=[]
    for p in pts:
        x,y,z,h,w=p;nx,ny=-math.sin(h),math.cos(h)
        for off in [inner(w),outer(w)]:vs.append((x+side*off*nx,y+side*off*ny,z+lift))
    for i in range(len(pts)-1):
        mid=tuple((a+b)/2 for a,b in zip(pts[i],pts[i+1]))
        if skip and skip(mid):continue
        fs.append((2*i,2*i+2,2*i+3,2*i+1) if side==1 else (2*i,2*i+1,2*i+3,2*i+2))
    return mesh(name,vs,fs,mat,col)
for seg in segments:
    pts=seg['points']
    # Insert exact garage opening stations, avoiding 25 cm cut quantisation.
    if seg['name'] in ['ReverseAisle','ParallelLane']:
        xs=[rx0,rx1,rx0-pad,rx1+pad] if seg['name']=='ReverseAisle' else [px0,px1,px0-pad,px1+pad]
        p=pts[0]; pts=pts+[(x,p[1],0,p[3],p[4]) for x in xs]
        pts=sorted(pts,key=lambda p:p[0],reverse=seg['name']=='ParallelLane')
    for side in [-1,1]:
        strip_path('LINE_'+seg['name']+('_L' if side==1 else '_R'),pts,side,lambda w:w/2,lambda w:w/2+lw,skip=lambda p:opening(seg,p,side))
        distance=0
        for a,b in zip(pts,pts[1:]):
            length=math.hypot(b[0]-a[0],b[1]-a[1]);mid=tuple((x+y)/2 for x,y in zip(a,b));distance+=length
            if opening(seg,mid,side,True):continue
            edge=[]
            for p in [a,b]:
                x,y,z,h,w=p;edge.append((x-side*(w/2+pad)*math.sin(h),y+side*(w/2+pad)*math.cos(h),z))
            # Outer direction is left of ordered a,b.
            if side==-1:edge.reverse()
            add_curb(*edge,int(distance/.5))

# Flat boundary helpers; strips always lie outside the measured clear area.
rect('LINE_Reverse_Left',rx0-lw,rx0,rback-lw,rfront,lift,white)
rect('LINE_Reverse_Right',rx1,rx1+lw,rback-lw,rfront,lift,white)
rect('LINE_Reverse_Back',rx0,rx1,rback-lw,rback,lift,white)
rect('LINE_Parallel_West',px0-lw,px0,popen,pback+lw,lift,white)
rect('LINE_Parallel_East',px1,px1+lw,popen,pback+lw,lift,white)
rect('LINE_Parallel_Back',px0,px1,pback,pback+lw,lift,white)
def dashed(name,a,b,width=lw,mat=white):
    a=Vector(a);b=Vector(b);d=b-a;length=d.length;u=d.normalized();n=Vector((-u.y,u.x,0))*width/2;vs=[];fs=[]
    for k in range(math.ceil(length/2)):
        lo=a+u*(2*k);hi=a+u*min(length,2*k+1);j=len(vs)
        vs.extend([lo-n,hi-n,hi+n,lo+n]);fs.append((j,j+1,j+2,j+3))
    return mesh(name,[tuple(x) for x in vs],fs,mat,'Markings')
dashed('LINE_Reverse_Opening',(rx0,rfront+lw/2,lift),(rx1,rfront+lw/2,lift))
dashed('LINE_Parallel_Opening',(px0,popen-lw/2,lift),(px1,popen-lw/2,lift))
control_left=6;control_right=rx1+D['reverse']['control_each_side']
for name,x in [('Left',control_left-lw/2),('Right',control_right+lw/2)]:dashed('LINE_Reverse_Control_'+name,(x,rfront,lift),(x,16+rw/2,lift))

def curb_line(a,b):
    a=Vector(a);b=Vector(b);v=b-a;N=math.ceil(v.length/.5)
    for i in range(N):add_curb(tuple(a+v*i/N),tuple(a+v*(i+1)/N),i)
# Ordered so left normal points outside the parking bays.
for a,b in [((rx0-pad,rfront-pad,0),(rx0-pad,rback-pad,0)),((rx0-pad,rback-pad,0),(rx1+pad,rback-pad,0)),((rx1+pad,rback-pad,0),(rx1+pad,rfront-pad,0))]:
    # Garage outside is on the right of this counterclockwise boundary.
    curb_line(b,a)
for a,b in [((px0-pad,popen+pad,0),(px0-pad,pback+pad,0)),((px0-pad,pback+pad,0),(px1+pad,pback+pad,0)),((px1+pad,pback+pad,0),(px1+pad,popen+pad,0))]:curb_line(a,b)
# Right-angle lines: two L-shaped boundaries, leaving entrance/exit open.
rect('LINE_RightAngle_OuterEast',east,east+lw,south-lw,north,lift,white)
rect('LINE_RightAngle_OuterSouth',west,east,south-lw,south,lift,white)
rect('LINE_RightAngle_InnerWest',inner_x-lw,inner_x,inner_y,north,lift,white)
rect('LINE_RightAngle_InnerNorth',west,inner_x,inner_y,inner_y+lw,lift,white)
for a,b in [((east+pad,north,0),(east+pad,south-pad,0)),((east+pad,south-pad,0),(west,south-pad,0)),((west,inner_y+pad,0),(inner_x-pad,inner_y+pad,0)),((inner_x-pad,inner_y+pad,0),(inner_x-pad,north,0))]:curb_line(b,a)
for name,offset in [('Stop',0),('Before',-.65),('After',.65)]:
    s=12+offset;w=Q['ramp_stop_line_width'] if not offset else lw
    vs=[(26+s-w/2,63.25,ramp_z(s-w/2)+lift),(26+s+w/2,63.25,ramp_z(s+w/2)+lift),(26+s+w/2,66.75,ramp_z(s+w/2)+lift),(26+s-w/2,66.75,ramp_z(s-w/2)+lift)]
    mesh('LINE_Ramp_'+name,vs,[(0,1,2,3)],yellow,'Markings')
curbs=mesh('CURBS_BlackYellow',curbverts,curbfaces,yellow,'Facilities');curbs.data.materials.append(black)
for p,mi in zip(curbs.data.polygons,curbmats):p.material_index=mi

# Presentation and technical labels exist in both checkpoints.
def text_obj(name,text,loc,size,mat=white,col='Facilities',rotation=(0,0,0)):
    d=bpy.data.curves.new(name,'FONT');d.body=text;d.size=size;d.align_x='CENTER';d.align_y='CENTER';d.extrude=.001
    o=bpy.data.objects.new(name,d);C[col].objects.link(o);o.location=loc;o.rotation_euler=rotation;d.materials.append(mat);return o
# Native Chinese font is loaded if available and packed with the scene.
fontpath='/System/Library/Fonts/PingFang.ttc'
font=bpy.data.fonts.load(fontpath) if Path(fontpath).exists() else None

def camera(name,loc,target,scale):
    d=bpy.data.cameras.new(name);d.type='ORTHO';d.ortho_scale=scale;d.lens=45
    o=bpy.data.objects.new(name,d);C['Presentation'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
cams={}
cams['01_overview']=camera('CAM_Overview',(127,-115,137),(50,36,0),130)
cams['02_top']=camera('CAM_Top',(50,37.5,140),(50,37.5,0),108)
cams['03_reverse']=camera('CAM_Reverse',(30,-13,34),(15,14,0),30)
cams['04_parallel']=camera('CAM_Parallel',(39,17,35),(21,46,0),28)
cams['05_hill']=camera('CAM_Hill',(80,21,37),(55,65,1),65)
cams['06_s_curve']=camera('CAM_SCurve',(110,12,40),(84,40,0),31)
cams['07_right_angle']=camera('CAM_RightAngle',(96,-5,32),(72,22,0),24)
for body,loc in [('01  REVERSE',(14,4,0.02)),('02  PARALLEL',(21,52,0.02)),('03  HILL START',(54,70,0.02)),('04  S-CURVE',(83,28,0.02)),('05  RIGHT ANGLE',(72,12,0.02))]:text_obj('LABEL_'+body,body,loc,.6,cream,'Presentation')
# Separate, toggleable measured-dimension layer.
for label,loc in [(f"{D['reverse']['width']:.3f} m",((rx0+rx1)/2,rback-.9,.05)),(f"{D['reverse']['length']:.3f} m",(rx1+1.4,(rfront+rback)/2,.05)),(f"{D['parallel']['length']:.3f} m",((px0+px1)/2,pback+.8,.05)),('R 7.500 / 4.000 m',(84,38,.05)),('10% / R30',(52,65,peak+.1)),('3.908 m',(ax,25,.05))]:text_obj('DIM_'+label,label,loc,.4,blue,'Dimensions')
C['Dimensions'].hide_render=True;C['Dimensions'].hide_viewport=True
world=bpy.data.worlds.new('C1_Daylight');world.use_nodes=True;scene.world=world
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.59,.70,.85,1);bg.inputs['Strength'].default_value=.45
sun_data=bpy.data.lights.new('Sun_afternoon','SUN');sun_data.energy=2.6;sun_data.angle=math.radians(12)
sun=bpy.data.objects.new('Sun_afternoon',sun_data);C['Presentation'].objects.link(sun);sun.rotation_euler=(math.radians(27),math.radians(-25),math.radians(-25))
scene.camera=cams['01_overview'];scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene['parameter_file']='//../parameters.json';scene['scope']='Blender only; historical supplied dimensions; no driving simulation'
scene['route_order']='Entrance > Reverse > Parallel > Hill > S curve > Right angle > Exit'
scene['references']='//../references/manifest.json'
scene['ramp_peak_m']=peak;scene['ramp_horizontal_m']=total
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=110;area.spaces.active.region_3d.view_location=Vector((50,37.5,0))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/china_subject2_v01_geometry.blend'))
print('CHECKPOINT geometry saved',flush=True)

# Surface seams, rubber traces, arrows, drains and site furniture.
def ribbon_line(name,pts,width,mat,col='Facilities'):
    vs=[]
    for i,p in enumerate(pts):
        p=Vector(p);d=Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(i-1,0)]);d.z=0;d.normalize();n=Vector((-d.y,d.x,0))*width/2;vs.extend([tuple(p-n),tuple(p+n)])
    return mesh(name,vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(pts)-1)],mat,col)
for seg in segments:
    if seg['material']!=concrete:continue
    distance=0;last=-10
    for a,b in zip(seg['points'],seg['points'][1:]):
        distance+=math.hypot(b[0]-a[0],b[1]-a[1])
        if distance-last>=4:
            x,y,z,h,w=b;n=Vector((-math.sin(h),math.cos(h),0));p=Vector((x,y,z+.0006))
            ribbon_line('DETAIL_Joint_'+seg['name']+'_'+str(round(distance)),[p-n*(w/2+.3),p+n*(w/2+.3)],.012,joint);last=distance
    if seg.get('exam') in ['s_curve','ramp']:
        pts=seg['points']
        for off in [-.71,.71]:
            # Short separated traces, not a continuous artificial racing line.
            for start in range(30,len(pts)-40,100):
                track=[(x-off*math.sin(h),y+off*math.cos(h),z+.001) for x,y,z,h,w in pts[start:start+24]]
                ribbon_line('DETAIL_Tyre_'+seg['name']+'_'+str(off)+'_'+str(start),track,.035,tiremat)
# Bay slab seams and small irregular cracks.
for x in [8,12,16,20,24]:ribbon_line('DETAIL_ReverseSlab_'+str(x),[(x,rfront+.18,.0006),(x,19.45,.0006)],.012,joint)
for xx,yy in [(18,17.7),(22,45.1),(14.2,8),(ax,24)]:
    pts=[(xx+i*.16,yy+random.uniform(-.07,.07),.001) for i in range(7)]
    ribbon_line('DETAIL_Crack_'+str(xx),pts,.006,joint)
rect('DETAIL_ReverseRepair',21,23,14,15,.0007,patchmat,'Facilities')
rect('DETAIL_ParallelRepair',18.2,19.7,43.1,44.2,.0007,patchmat,'Facilities')

def arrow(name,x,y,h,z=0):
    coords=[(-1,-.16),(.35,-.16),(.35,-.46),(1,.0),(.35,.46),(.35,.16),(-1,.16)]
    vs=[(x+a*math.cos(h)-b*math.sin(h),y+a*math.sin(h)+b*math.cos(h)) for a,b in coords]
    polygon(name,vs,z+lift,white,'Markings')
for i,(x,y,h) in enumerate([(2,16,0),(30,16,0),(39,28,math.pi/2),(26,44,math.pi),(5,54,math.pi/2),(22,65,0),(ramp_end+8,55,-math.pi/2),(ax,30,-math.pi/2),(58,exit_y,math.pi),(40,4,-math.pi/2)]):arrow('ARROW_'+str(i),x,y,h)
# Jointed ramp side retaining panels, with drainage openings at the base.
for x in range(29,82,4):
    z=ramp_z(x-26)
    for y in [62.78,67.22]:
        if z>.3:box('DETAIL_RetainingJoint',(x,y,z/2),(.012,.012,z),joint)
for i,(x,y) in enumerate([(10,12),(24,12),(17,46),(25,46),(38,32),(6,58),(30,63),(82,63),(ax+2.12,25)]):
    box('DRAIN_Frame_'+str(i),(x,y,.007),(.65,.30,.014),black)
    for k in range(9):box('DRAIN_Grate_'+str(i)+'_'+str(k),(x-.27+k*.0675,y,.018),(.025,.28,.018),metal)

def sign(index,label,x,y):
    box('SIGN_Post_'+str(index),(x,y,.9),(.08,.08,1.8),metal)
    box('SIGN_Board_'+str(index),(x,y,1.9),(2.6,.10,.90),blue,bevel=.035)
    o=text_obj('SIGN_Text_'+str(index),f'{index:02d}  {label}',(x,y-.056,1.94),.28,white,rotation=(math.pi/2,0,0))
    if font:o.data.font=font
for args in [(1,'倒车入库',24,9),(2,'侧方停车',29,49),(3,'坡道起步',29,69),(4,'曲线行驶',78,45),(5,'直角转弯',80,22)]:sign(*args)
# Entrance booth, windows, canopy; separate from driving surfaces.
box('BUILDING_Reception',(6.5,6,1.5),(5,4,3),cream,bevel=.035)
box('BUILDING_Roof',(6.5,6,3.13),(5.6,4.6,.22),blue,bevel=.03)
box('BUILDING_Window',(6.5,8.01,1.8),(3.4,.035,1.1),glass)
box('BUILDING_Door',(9.01,5.7,1.1),(.04,1.1,2.2),glass)
t=text_obj('BUILDING_Name','C1  驾驶训练场',(6.5,8.05,2.65),.32,blue,rotation=(math.pi/2,0,math.pi))
if font:t.data.font=font
# Simple perimeter mesh fence. Entry on west, exit on south.
for edge,a,b in [('N',(2,73),(98,73)),('E',(98,2),(98,73)),('W1',(2,2),(2,10)),('W2',(2,22),(2,73)),('S1',(2,2),(35,2)),('S2',(45,2),(98,2))]:
    a=Vector((*a,0));b=Vector((*b,0));length=(b-a).length;n=math.ceil(length/3);u=(b-a).normalized()
    for i in range(n+1):
        p=a+(b-a)*i/n;box('FENCE_Post_'+edge+str(i),(p.x,p.y,.8),(.07,.07,1.6),metal)
    for z in [.45,1.45]:ribbon_line('FENCE_Rail_'+edge+str(z),[(a.x,a.y,z),(b.x,b.y,z)],.045,metal)
    for i in range(math.ceil(length/.22)):
        p=a+u*i*.22;box('FENCE_Wire_'+edge+str(i),(p.x,p.y,.9),(.012,.012,1.15),metal)

# Keep vegetation outside pavement, bay envelopes, hut and signs.
all_pts=[p for seg in segments for p in seg['points'][::4]]
def free_land(x,y,margin=2.5):
    if not (3<x<97 and 3<y<72):return False
    for px,py,z,h,w in all_pts:
        if (x-px)**2+(y-py)**2<(w/2+pad+margin)**2:return False
    for x0,x1,y0,y1 in [(rx0-1,rx1+1,rback-1,rfront+1),(px0-1,px1+1,popen-1,pback+1),(3,10,3,10),(west-1,east+1,south-1,north+1)]:
        if x0-margin<x<x1+margin and y0-margin<y<y1+margin:return False
    return True

def tree(i,x,y):
    h=random.uniform(3.5,5.5)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.10,depth=h*.6,location=(x,y,h*.3-.02));o=bpy.context.object;o.name='TREE_Trunk_'+str(i);move_collection(o,'Landscape');o.data.materials.append(wood)
    for k in range(3):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(x+random.uniform(-.45,.45),y+random.uniform(-.45,.45),h*.64+k*.32))
        o=bpy.context.object;o.name='TREE_Crown_'+str(i)+'_'+str(k);o.scale=(random.uniform(.9,1.4),random.uniform(.9,1.4),random.uniform(.9,1.3));move_collection(o,'Landscape');o.data.materials.append(leaves[i%3])
        for p in o.data.polygons:p.use_smooth=True
count=0
for y in range(8,70,9):
    for x in range(9,95,10):
        xx=x+random.uniform(-2,2);yy=y+random.uniform(-2,2)
        if free_land(xx,yy,3.1) and random.random()<.65:tree(count,xx,yy);count+=1
# A few thousand small grass blades, all one mesh.
gvs=[];gfs=[]
for i in range(8500):
    x=random.uniform(3,97);y=random.uniform(3,72)
    if not free_land(x,y,.25):continue
    h=random.uniform(.05,.16);j=len(gvs);gvs.extend([(x-.035,y,-.02),(x+.035,y,-.02),(x+.015,y+.02,h)]) ;gfs.append((j,j+1,j+2))
mesh('GRASS_Sparse_tufts',gvs,gfs,leaves[1],'Landscape')
print('DETAILS complete, loading car',flush=True)

# Import only the calibrated vehicle collection; never its old road/camera/lighting.
carfile=ROOT/'assets/mercedes_amg_c63_reference.blend'
with bpy.data.libraries.load(str(carfile),link=False) as (src,dst):
    dst.collections=['REFERENCE_Mercedes_AMG_C63_EXCLUDE_FROM_MAP']
carcoll=dst.collections[0]
carobjs=list(carcoll.all_objects)
root=next(o for o in carobjs if o.type=='EMPTY')
for o in carobjs:
    if o.name not in C['ReferenceCar_HIGH'].objects:C['ReferenceCar_HIGH'].objects.link(o)
bpy.data.collections.remove(carcoll)
root.location=((rx0+rx1)/2,(rfront+rback)/2,0);root.rotation_euler=(0,0,math.pi/2)
bpy.context.view_layer.update()
# Shared placement parent; lower-detail mesh is baked once for viewport performance.
meshes=[o for o in carobjs if o.type=='MESH'];tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
ratio=min(1,230000/tri)
proxy_tri=0
for i,o in enumerate(meshes):
    p=o.copy();p.data=o.data.copy();p.name='PROXY_'+o.name;C['ReferenceCar_PROXY'].objects.link(p);p.parent=root
    mod=p.modifiers.new('Viewport reduction','DECIMATE');mod.ratio=ratio
    deps=bpy.context.evaluated_depsgraph_get();evalob=p.evaluated_get(deps);m=bpy.data.meshes.new_from_object(evalob,preserve_all_data_layers=True,depsgraph=deps)
    old=p.data;p.modifiers.clear();p.data=m
    if old.users==0:bpy.data.meshes.remove(old)
    proxy_tri+=sum(len(f.vertices)-2 for f in m.polygons)
    print('PROXY',i+1,len(meshes),flush=True)
# hide_set is per-view-layer and leaves evaluated world transforms valid.
for o in meshes:o.hide_set(True)
C['ReferenceCar_PROXY'].hide_render=True
scene['car_high_triangles']=tri;scene['car_proxy_triangles']=proxy_tri
scene['car_display']='High-detail render / lightweight viewport; both share placement parent'
scene['asset_license']='C63 by wishingchain / Free3D Personal Use License. Local use; source and derivative blends excluded from Git.'
assert proxy_tri<=P['display_vehicle']['proxy_triangle_budget'],proxy_tri
# Pack font/resources and make local asset references portable.
bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative()
scene.camera=cams['01_overview']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/china_subject2_v02_detailed.blend'))
manifest={'route_segments':[{'name':s['name'],'start':list(s['points'][0]),'end':list(s['points'][-1]),'circle_center':s.get('circle_center')} for s in segments],
 'parking':{'reverse':[rx0,rx1,rback,rfront],'parallel':[px0,px1,popen,pback]},'right_angle':right_coords,
 'ramp':{'run':run,'rise':rise,'up':up,'height':peak,'total':total},'car_triangles':tri,'proxy_triangles':proxy_tri,'trees':count,
 'previews':{k:v.name for k,v in cams.items()}}
(ROOT/'reports/build_manifest.json').write_text(json.dumps(manifest,indent=2))
print('SUCCESS detailed scene saved',flush=True)
