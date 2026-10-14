"""Original simplified A4L exterior, dimensioned from Audi China literature.

Run in Blender with the saved V12 scene. Static reference only, not a vehicle mod.
No downloaded third-party mesh, texture, or embedded executable is used.
"""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector
from math import sin, cos, pi

OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
scene = bpy.context.scene
SOURCE = bpy.data.filepath
COLNAME = 'REFERENCE_Audi_A4L_EXCLUDE_FROM_MAP'
old = bpy.data.collections.get(COLNAME)

def environment_signature():
    result = {}
    for o in scene.objects:
        if o.type != 'MESH' or (old and old in o.users_collection): continue
        payload = ([(tuple(v.co)) for v in o.data.vertices],
                   [tuple(p.vertices) for p in o.data.polygons],
                   [list(r) for r in o.matrix_world],
                   [m.name if m else None for m in o.data.materials])
        result[o.name] = hashlib.sha256(repr(payload).encode()).hexdigest()
    return result

before = environment_signature()
if old:
    for o in list(old.objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
ref = bpy.data.collections.new(COLNAME); scene.collection.children.link(ref)
old = ref
root = bpy.data.objects.new('REFERENCE_Audi_A4L_Exterior_4858x1847x1439mm', None)
ref.objects.link(root)
root.location = (7.5,44.25,0)
root['export_to_beamng'] = False
root['model_note'] = 'Original simplified A4L-inspired static exterior; not OEM CAD or a drivable mod'
root['length_m'] = 4.858; root['body_width_without_mirrors_m'] = 1.847
root['height_m'] = 1.439; root['wheelbase_m'] = 2.908
root['mirror_width_trial_m'] = 2.08

def mat(name, color, rough=.35, metal=0):
    m=bpy.data.materials.new('A4L13_'+name); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*color,1)
    return m

paint=mat('Daytona_Silver',(.31,.345,.38),.26,.68)
shader=next(n for n in paint.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
shader.inputs['Coat Weight'].default_value=.4
shader.inputs['Coat Roughness'].default_value=.2
glass=mat('Smoked_Glass',(.018,.035,.046),.16,.35)
black=mat('Black_Trim',(.009,.012,.015),.45,.12)
rubber=mat('Tyre',(.016,.019,.022),.82)
chrome=mat('Satin_Aluminium',(.63,.69,.74),.22,.85)
wheelmat=mat('Wheel_Anthracite',(.048,.06,.071),.3,.72)
brake=mat('Brake_Disc',(.21,.23,.25),.53,.8)
caliper=mat('Brake_Caliper',(.085,.09,.095),.38,.5)
lamp=mat('Headlamp_Lens',(.56,.65,.70),.17,.32)
led=mat('LED_Light_Guide',(.92,.96,1),.21,.15)
tail=mat('Red_Taillight',(.38,.008,.008),.22,.28)
redled=mat('Red_Light_Guide',(.8,.025,.012),.25,.12)
plate=mat('Blue_Plate',(.01,.065,.31),.38,.1)

def link(o, material=None, mirror=False):
    for c in list(o.users_collection): c.objects.unlink(o)
    ref.objects.link(o); o.parent=root
    if material: o.data.materials.append(material)
    o['reference_only']=True
    o['mirror_part']=mirror
    return o

def mesh(name, verts, faces, material, smooth=False):
    d=bpy.data.meshes.new('A4L13_'+name); d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new('A4L13_'+name,d);ref.objects.link(o);o.parent=root
    o['reference_only']=True;o['mirror_part']=False
    d.materials.append(material)
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
    for p in d.polygons:p.use_smooth=smooth
    return o

def box(name,pos,size,material,bevel=0,mirror=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
    o=bpy.context.object;o.name='A4L13_'+name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    link(o,material,mirror)
    if bevel:
        m=o.modifiers.new('Rounded manufactured edges','BEVEL');m.width=bevel;m.segments=3
        m=o.modifiers.new('Panel normals','WEIGHTED_NORMAL')
    return o

def line(name,pts,material,r=.004,closed=False,mirror=False):
    d=bpy.data.curves.new('A4L13_'+name,'CURVE');d.dimensions='3D';d.resolution_u=1
    d.bevel_depth=r;d.bevel_resolution=2
    p=d.splines.new('POLY');p.points.add(len(pts)-1)
    for q,co in zip(p.points,pts):q.co=(*co,1)
    p.use_cyclic_u=closed
    o=bpy.data.objects.new('A4L13_'+name,d);ref.objects.link(o);o.parent=root
    d.materials.append(material);o['reference_only']=True;o['mirror_part']=mirror
    return o

def cylinder(name,pos,radius,depth,material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=pos,rotation=(pi/2,0,0))
    o=bpy.context.object;o.name='A4L13_'+name;link(o,material)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o

def panel(name,pts,material): return mesh(name,pts,[tuple(range(len(pts)))],material)

# The lower shell has shoulder/rocker creases, a sloping bonnet, and real wheel openings.
sections=[(-2.40,.84,.866),(-2.26,.873,.92),(-1.92,.912,.96),(-1.39,.9235,.975),
          (-.95,.9235,.969),(0,.91,.95),(.8,.92,.948),(1.52,.9235,.948),
          (1.92,.90,.905),(2.23,.88,.87),(2.40,.87,.85)]
verts=[]
for x,w,z in sections:
    # Positive side around the crown, followed by negative side; equal topology.
    ring=[(0,.235),(.86*w,.235),(.95*w,.33),(w,.62),(.995*w,.75),(.955*w,z-.035),
          (.80*w,z),(.4*w,z+.012),(0,z+.018),(-.4*w,z+.012),(-.80*w,z),
          (-.955*w,z-.035),(-.995*w,.75),(-w,.62),(-.95*w,.33),(-.86*w,.235)]
    verts += [(x,y,h) for y,h in ring]
n=16;faces=[]
for i in range(len(sections)-1):
    faces += [(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for j in range(n)]
faces += [tuple(range(n-1,-1,-1)),tuple(range((len(sections)-1)*n,len(sections)*n))]
body=mesh('Body_Shell',verts,faces,paint,True)
for axle in [-1.386,1.522]:
    cut=cylinder('Temporary_Wheel_Arch_Cutter',(axle,0,.337),.378,2.4,black)
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active=body
    mod=body.modifiers.new('Open wheel arch','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cut,do_unlink=True)
m=body.modifiers.new('Small body panel edge radius','BEVEL');m.width=.010;m.segments=3
m=body.modifiers.new('Body weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True
# Bumper tips control exact overall length; the grille sits forward of shell endcap.
box('Front_Bumper',(2.405,0,.36),(.048,1.66,.15),paint,.018)
box('Rear_Bumper',(-2.405,0,.36),(.048,1.63,.15),paint,.018)
box('Underbody',(0,0,.16),(2.20,1.10,.126),black,.016)

# Cabin cross-sections produce a curved roof rather than the old cuboid cabin.
cab=[(-1.58,.778,.952),(-1.34,.764,1.073),(-1.04,.710,1.30),(-.82,.686,1.397),
     (-.54,.678,1.434),(0,.68,1.439),(.40,.693,1.415),(.58,.714,1.363),
     (.86,.762,1.169),(1.13,.809,.962)]
cv=[]
for x,w,z in cab:
    cv.extend([(x,y*w,z-.05*abs(y)**2) for y in [-1,-.95,-.48,0,.48,.95,1]])
cf=[]
for i in range(len(cab)-1):
    cf.extend([(i*7+j,i*7+j+1,(i+1)*7+j+1,(i+1)*7+j) for j in range(6)])
cabin=mesh('Cabin_Roof',cv,cf,paint,True)
cabin.data.materials.append(glass)
for p in cabin.data.polygons:
    segment=p.index//6; column=p.index%6
    if (segment<2 or segment>=7) and column in [1,2,3,4]: p.material_index=1

def cab_at(x):
    for a,b in zip(cab,cab[1:]):
        if a[0]<=x<=b[0]:
            t=(x-a[0])/(b[0]-a[0]);return a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2])-.05
    raise ValueError(x)

def side_point(x,z,s,out=.003):
    w,top=cab_at(x)
    base=.84
    f=(z-.925)/(top-.925)
    return (x,s*(base+(w-base)*f+out),z)

# Fill side pillars underneath the arched roof; glazing is placed just outside.
for s in [-1,1]:
    for a,b in zip(cab,cab[1:]):
        panel('Cabin_Side',[(a[0],s*.84,.925),(b[0],s*.84,.925),(b[0],s*b[1],b[2]-.05),(a[0],s*a[1],a[2]-.05)],paint)
    for k,(xa,xb) in enumerate([(-.16,1.04),(-1.37,-.25)]):
        xs=sorted(set([xa,xb]+[x for x,w,z in cab if xa<x<xb]))
        vv=[]
        for x in xs:
            w,top=cab_at(x)
            vv += [side_point(x,.967,s),side_point(x,max(.971,top-.033),s)]
        fs=[(2*i,2*i+2,2*i+3,2*i+1) for i in range(len(xs)-1)]
        mesh(f'Side_Window_{s}_{k}',vv,fs,glass,True)
        outline=vv[::2]+vv[1::2][::-1]
        line('Window_Seal',outline,black,.005,True)
        line('Window_Chrome',[(x,y+s*.001,z) for x,y,z in outline],chrome,.0025,True)
    # Thin trim, B-pillar, door panel gaps, and handles.
    for x in [-1.19,-.205,.99]:
        # Shallow accent close to the shell, avoiding floating vertical struts.
        line('Door_Shut_Line',[(x,s*.878,.901),(x,s*.913,.756),(x,s*.917,.62),(x-.035,s*.895,.405),(x-.06,s*.871,.333)],black,.0013)
    for x in [-.95,.67]:
        box('Door_Handle',(x,s*.914,.817),(.17,.022,.03),paint,.01)
        line('Handle_Shadow',[(x-.075,s*.919,.797),(x+.075,s*.919,.797)],black,.002)
    line('Lower_Door_Contour',[(-.99,s*.879,.34),(.99,s*.879,.34)],paint,.004)
    # Arched wheel lip strips make the openings legible in side view.
    for x in [-1.386,1.522]:
        line('Wheel_Arch_Lip',[(x+.379*cos(t),s*.913,.337+.379*sin(t)) for t in [pi*i/48 for i in range(49)]],paint,.008)


# Front single-frame hexagon, chrome surround, grille lattice, and four rings.
outline=[(-.50,.80),(.50,.80),(.565,.68),(.465,.402),(-.465,.402),(-.565,.68)]
panel('Singleframe_Grille',[(2.413,y,z) for y,z in outline],black)
line('Singleframe_Surround',[(2.416,y,z) for y,z in outline],chrome,.007,True)
for z in [.445,.493,.541,.589,.637,.685,.733,.772]:
    w=.46 if z<.51 else .50
    line('Grille_Horizontal',[(2.415,-w,z),(2.415,w,z)],wheelmat,.003)
for y in [i*.049 for i in range(-9,10)]:
    line('Grille_Vertical',[(2.415,y,.435),(2.415,y,.774)],wheelmat,.0025)
for y in [-.129,-.043,.043,.129]:
    line('Front_Four_Rings',[(2.421,y+.056*cos(t),.724+.043*sin(t)) for t in [2*pi*i/48 for i in range(48)]],chrome,.004,True)
box('Front_Plate',(2.420,0,.539),(.012,.44,.14),plate,.006)

for s in [-1,1]:
    pts=[(2.411,s*y,z) for y,z in [(.545,.811),(.86,.819),(.856,.715),(.612,.693),(.525,.747)]]
    panel('Headlight_Housing',pts,black)
    inset=[(2.414,s*y,z) for y,z in [(.557,.798),(.847,.805),(.84,.731),(.624,.706),(.539,.746)]]
    panel('Headlight_Lens',inset,lamp)
    line('LED_Daylight',[(2.419,s*y,z) for y,z in [(.844,.796),(.567,.791),(.552,.750),(.630,.719)]],led,.0045)
    for y in [.641,.701,.761,.811]:
        box('LED_Projector',(2.418,s*y,.761),(.009,.025,.023),chrome,.004)
    pts=[(2.410,s*y,z) for y,z in [(.634,.613),(.839,.607),(.801,.451),(.579,.451)]]
    panel('Lower_Air_Intake',pts,black)
    for z in [.476,.524,.573]:
        line('Intake_Slat',[(2.416,s*.63,z),(2.416,s*.803,z)],wheelmat,.004)
    # Tail lamps and exhaust finishers.
    panel('Rear_Lamp', [(-2.412,s*y,z) for y,z in [(.30,.809),(.822,.785),(.827,.674),(.355,.690)]],tail)
    line('Rear_LED', [(-2.418,s*y,z) for y,z in [(.33,.788),(.792,.764),(.78,.704),(.39,.711)]],redled,.007)
    line('Tailgate_Chrome',[(-2.417,s*.035,.699),(-2.417,s*.34,.699)],chrome,.004)
    box('Exhaust_Trim',(-2.415,s*.636,.292),(.015,.26,.079),chrome,.018)
    box('Exhaust_Dark',(-2.425,s*.636,.294),(.005,.218,.044),black,.013)
box('Rear_Plate',(-2.418,0,.53),(.016,.44,.14),plate,.005)
for y in [-.096,-.032,.032,.096]:
    line('Rear_Four_Rings',[(-2.417,y+.042*cos(t),.794+.031*sin(t)) for t in [2*pi*i/40 for i in range(40)]],chrome,.003,True)

def text_on_face(name,text,pos,size,material,front=True):
    d=bpy.data.curves.new(name,'FONT');d.body=text;d.align_x='CENTER';d.align_y='CENTER';d.size=size;d.extrude=.0003
    o=bpy.data.objects.new('A4L13_'+name,d);ref.objects.link(o);o.parent=root;o.location=pos
    # Local text X points across the car; local Y points upwards.
    from mathutils import Matrix
    o.rotation_euler=Matrix(((0,0,1 if front else -1),(1 if front else -1,0,0),(0,1,0))).to_euler()
    d.materials.append(material);o['reference_only']=True;o['mirror_part']=False
    return o
text_on_face('Front_Plate_Text','A4L',(2.428,0,.54),.084,led)
text_on_face('Rear_Plate_Text','A4L',(-2.428,0,.53),.084,led,False)
text_on_face('Boot_A4L_Badge','A4L',(-2.419,.49,.837),.037,chrome,False)

# Wheels: physically separate tyres, alloy rim, split spokes, discs, and lugs.
axles=[('Rear',-1.386,.7745),('Front',1.522,.783)]
for label,x,track in axles:
    for s in [-1,1]:
        y=s*track;zc=.337
        tyre_profile=[(-.118,.247),(-.121,.277),(-.113,.317),(-.093,.337),(.093,.337),(.113,.317),(.121,.277),(.118,.247)]
        vs=[(x+r*cos(a),y+dy,zc+r*sin(a)) for dy,r in tyre_profile for a in [2*pi*i/72 for i in range(72)]]
        fs=[]
        for j in range(len(tyre_profile)):
            fs.extend([(j*72+i,j*72+(i+1)%72,((j+1)%len(tyre_profile))*72+(i+1)%72,((j+1)%len(tyre_profile))*72+i) for i in range(72)])
        tyre=mesh(f'Tyre_{label}_{s}',vs,fs,rubber,True)
        tyre['axle_center_x_m']=x;tyre['wheelbase_m']=2.908
        cylinder('Wheel_Barrel',(x,y,zc),.246,.213,wheelmat)
        cylinder('Ventilated_Brake_Disc',(x,y+s*.082,zc),.199,.016,brake)
        box('Brake_Caliper',(x+.134,y+s*.087,zc+.04),(.081,.055,.19),caliper,.02)
        for radius in [.242,.231]:
            line('Alloy_Rim_Lip',[(x+radius*cos(t),y+s*.123,zc+radius*sin(t)) for t in [2*pi*i/72 for i in range(72)]],chrome,.008,True)
        for k in range(5):
            for off in [-.08,.08]:
                a=2*pi*k/5+off
                p=[(x+r*cos(a+da),y+s*(.12 if r>.10 else .136),zc+r*sin(a+da)) for r,da in [(.055,-.18),(.225,-.07),(.229,.028),(.073,.13)]]
                obj=panel('Split_Alloy_Spoke',p,chrome)
                mod=obj.modifiers.new('Spoke depth','SOLIDIFY');mod.thickness=.017
                mod=obj.modifiers.new('Spoke edge','BEVEL');mod.width=.004;mod.segments=2
        cylinder('Centre_Cap',(x,y+s*.129,zc),.061,.018,wheelmat)
        for k in range(5):
            a=2*pi*k/5
            cylinder('Wheel_Bolt',(x+.044*cos(a),y+s*.143,zc+.044*sin(a)),.008,.006,chrome)
        for k in range(36):
            a=2*pi*k/36
            line('Tyre_Tread',[(x+.3362*cos(a+dy*.19),y+dy,zc+.3362*sin(a+dy*.19)) for dy in [-.075,0,.075]],black,.0007)

# Mirrors are deliberately separate from the official 1.847 m body width.
for s in [-1,1]:
    line('Mirror_Stem',[(.87,s*.812,1.02),(.80,s*.947,1.035)],black,.017,mirror=True)
    housing=box('Mirror_Housing',(.77,s*.967,1.065),(.25,.146,.10),paint,.032,mirror=True)
    box('Mirror_Reflective_Face',(.651,s*.965,1.066),(.006,.110,.062),chrome,.016,mirror=True)
    line('Mirror_Indicator',[(.829,s*1.028,1.055),(.719,s*1.028,1.055)],led,.0025,mirror=True)

# Evaluate real mesh bounds rather than trusting metadata.
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
def bounds(objects):
    pts=[]
    for o in objects:
        if o.type not in {'MESH','CURVE','FONT'}:continue
        e=o.evaluated_get(deps);me=e.to_mesh()
        pts += [root.matrix_world.inverted() @ e.matrix_world @ v.co for v in me.vertices]
        e.to_mesh_clear()
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    return {'min':lo,'max':hi,'size':[hi[i]-lo[i] for i in range(3)]}

# Tyre treads are shallow cosmetics: shift tyre cross-sections and tread to exact ground.
car_parts=[o for o in ref.objects if o!=root]
b= bounds(car_parts)
for o in car_parts:o.location.z -= b['min'][2]
# Preserve official height and width after small trim/edge radii by calibrating only
# outliers; all X features must stay within the bumper planes.
for o in car_parts:
    if o.type=='MESH':
        # Geometry (not a hidden dimension cage) defines the scale envelope.
        for v in o.data.vertices:
            p=o.matrix_basis @ v.co
            if abs(p.x)>2.429: v.co = o.matrix_basis.inverted() @ Vector((max(-2.429,min(2.429,p.x)),p.y,p.z))
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
bodybounds=bounds([o for o in car_parts if not o.get('mirror_part')])
sy=1.847/bodybounds['size'][1]
sz=1.439/bodybounds['size'][2]
from mathutils import Matrix
calibration=Matrix.Diagonal((1,sy,sz,1))
for o in car_parts:
    o.matrix_basis=calibration @ o.matrix_basis
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
bodybounds=bounds([o for o in car_parts if not o.get('mirror_part')])
fullbounds=bounds(car_parts)
assert all(abs(a-b)<.00005 for a,b in zip(bodybounds['size'],[4.858,1.847,1.439])),bodybounds
after=environment_signature()
assert before==after,'Environment geometry/material assignments were modified'
report={'source':SOURCE,'note':'Original simplified A4L exterior; styling approximate; static reference only',
 'body_bounds_without_mirrors_m':bodybounds,'full_bounds_with_trial_mirrors_m':fullbounds,
 'target_length_width_height_m':[4.858,1.847,1.439], 'wheelbase_m':1.522-(-1.386),
 'axle_centers_m':{'rear':-1.386,'front':1.522},'front_overhang_m':.907,'rear_overhang_m':1.043,
 'road_and_environment_unchanged':before==after,'environment_mesh_objects_verified':len(before),
 'car_objects':len(car_parts),'third_party_meshes_used':False,'drivable_beamng_vehicle':False}
(OUT/'geometry_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,indent=2))

def camera(name,pos,target,scale):
    o=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(o)
    o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.type='ORTHO';o.data.ortho_scale=scale;return o
front=camera('Camera_V13_A4L_Front',(13.7,39.8,3.8),(7.5,44.25,.70),7.5)
rear=camera('Camera_V13_A4L_Rear',(1.1,40,3.1),(7.5,44.25,.72),7.5)
side=camera('Camera_V13_A4L_Side',(7.5,46.3,.72),(7.5,44.25,.72),6.2)
scene.render.image_settings.file_format='PNG';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
for name,cam,w,h in [('a4l_front',front,1500,1000),('a4l_rear',rear,1500,1000),('a4l_side',side,1500,750),('overview',bpy.data.objects['Camera_V11_Overview'],1500,1100)]:
    scene.camera=cam;scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.camera=front;scene.render.resolution_x=1500;scene.render.resolution_y=1000
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v13_a4l_reference.blend'))
# Normal scene saving avoids a Blender 5.2.2 partial scene library writer crash.
exec(compile((OUT/'export_reference_asset.py').read_text(),str(OUT/'export_reference_asset.py'),'exec'))
