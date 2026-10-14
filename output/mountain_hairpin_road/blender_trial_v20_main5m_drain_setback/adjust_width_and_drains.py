import bpy, sys, json, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'blender_trial_v10_smooth_hairpins'))
from road_profile import segments
scene=bpy.context.scene
def signature(ob):
    return hashlib.sha256(repr(([tuple(v.co) for v in ob.data.vertices],[tuple(f.vertices) for f in ob.data.polygons],list(map(list,ob.matrix_world)))).encode()).hexdigest()
road=bpy.data.objects['Road_Surface_Small_Concrete_3m']
road_before=signature(road)
car=bpy.data.objects['REFERENCE_Mercedes_AMG_C63_4756x1839x1426mm'];pose=car.matrix_world.copy()
guards={o.name:signature(o) for o in scene.objects if o.type=='MESH' and ('Guardrail' in o.name or o.name.startswith(('V16_Small_Rail','V16_Small_WBeam')))}
# Widen away from the small-road junction; the near-side edge remains Y=42.
main=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m']
main.name='Road_Surface_Main_Asphalt_5m';main['width_m']=5.
road['main_road_width_m']=5.
names=[main.name,'Terrain_Berms_and_Unguarded_Drops','Drainage_Channel_Clear_0p50m_Deep_0p60m','Drainage_Outer_Vegetated_Bank','Terrain_Block_Sides','Terrain_Block_Bottom','Sparse_Grass_Clumps']
for name in names:
    o=bpy.data.objects[name];inv=o.matrix_world.inverted()
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        if name in ['Drainage_Channel_Clear_0p50m_Deep_0p60m','Drainage_Outer_Vegetated_Bank']:
            p.y+=.5
        else:
            p.y+=.5*min(1.,max(0.,(p.y-42)/4.5))
        v.co=inv@p
    o.data.update()

coll=bpy.data.collections.new('V20_Drain_Setbacks');scene.collection.children.link(coll)
soil=bpy.data.materials['Terrain_Continuous_Grass_Earth']
def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);coll.objects.link(o);d.materials.append(mat)
    return o
def strip_faces(count,k):
    return [(i*k+j,(i+1)*k+j,(i+1)*k+j+1,i*k+j+1) for i in range(count-1) for j in range(k-1)]
def tree(o):
    return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons])
def hit(b,q):
    return b.ray_cast(Vector((float(q[0]),float(q[1]),20)),Vector((0,0,-1)))[0]
report={'main_paved_width_m':5.,'small_paved_width_m':3.,'main_drain_excluded_from_width':True,'setbacks':[],'beamng_updated':False}
for prefix,ss,cut,keep_before in [
    ('V16',np.linspace(12,segments[2]['s']-.12,151),18.,True),
    ('V17',np.linspace(segments[4]['s']+2,segments[4]['s']+segments[4]['length']-.15,151),segments[4]['s']+4.,False)]:
    ob=bpy.data.objects[prefix+'_Small_Road_U_Drain_Clear_0p50_Deep_0p60']
    rows=np.array([tuple(ob.matrix_world@v.co) for v in ob.data.vertices]).reshape(-1,6,3)
    # Insert an exact station at the new endpoint, then separate kept and filled rows.
    index=int(np.searchsorted(ss,cut));t=(cut-ss[index-1])/(ss[index]-ss[index-1]);r=rows[index-1]*(1-t)+rows[index]*t
    if keep_before: kept=np.concatenate([rows[:index],r[None]]);removed=np.concatenate([r[None],rows[index:]])
    else: kept=np.concatenate([r[None],rows[index:]]);removed=np.concatenate([rows[:index],r[None]])
    old=ob.data;d=bpy.data.meshes.new(ob.name+'_V20');d.from_pydata(kept.reshape(-1,3),[],strip_faces(len(kept),6));d.update()
    for m in old.materials:d.materials.append(m)
    ob.data=d
    # Fill the removed U-shaped trench to the existing two lip elevations.
    filled=removed[:,[0,5],:].copy()
    fill=mesh(prefix+'_V20_Filled_Drain_Shoulder',filled.reshape(-1,3),strip_faces(len(filled),2),soil)
    gf=fill.data.attributes.new('GrassFactor','FLOAT','POINT')
    for a in gf.data:a.value=.30
    for f in fill.data.polygons:f.use_smooth=True
    # Close the new termination against the restored earth.
    er=kept[-1] if keep_before else kept[0]
    mesh(prefix+'_V20_Drain_Terminal_Earth',er,[(0,1,2,3,4,5)],soil)
    # Original far-end soil cap loses its now-obsolete U-shaped recess.
    end=bpy.data.objects[prefix+'_Drain_End_Earth_'+('150' if keep_before else '0')]
    for j in [2,3]:end.data.vertices[j].co.z=end.data.vertices[0].co.z
    end.data.update()
    width=np.linalg.norm(kept[:,4,:2]-kept[:,1,:2],axis=1);depth=kept[:,1,2]-kept[:,2,2]
    assert np.max(np.abs(width-.5))<.001 and np.max(np.abs(depth-.6))<.001
    # The filled strip has no remaining trench; kept drain bottoms remain exposed.
    filltree=tree(fill);dtree=tree(ob);terrain=tree(bpy.data.objects['Terrain_Berms_and_Unguarded_Drops'])
    for i in np.linspace(1,len(filled)-2,6).astype(int):
        q=(filled[i,0]+filled[i,1])/2;h=hit(filltree,q)
        assert h is not None and abs(h.z-q[2])<.003
    for i in np.linspace(1,len(kept)-2,6).astype(int):
        q=(kept[i,2]+kept[i,3])/2;floor=hit(dtree,q);ground=hit(terrain,q)
        assert floor is not None and (ground is None or ground.z<floor.z-.015)
        assert hit(filltree,q) is None
    report['setbacks'].append({'drain':prefix,'endpoint_station_m':float(cut),'distance_from_curve_m':2. if keep_before else 4.,'side':'before_C1_entry' if keep_before else 'after_C2_exit','remaining_length_m':float(cut-ss[0] if keep_before else ss[-1]-cut),'clear_width_min_m':float(width.min()),'clear_width_max_m':float(width.max()),'depth_m':float(depth.mean()),'fill_and_open_trench_ray_checks':True})
assert signature(road)==road_before
assert car.matrix_world==pose
assert all(signature(bpy.data.objects[n])==s for n,s in guards.items())
assert max(v.co.y for v in main.data.vertices)-min(v.co.y for v in main.data.vertices)==5.
assert all(v.co.z==0 for v in main.data.vertices)
report.update(small_road_geometry_unchanged=True,small_car_pose_unchanged=True,guardrails_unchanged=True,main_elevation_m=0.)
# Update the existing shared-mesh two-car illustration for the new five-metre road.
meeting=bpy.data.collections['REFERENCE_Main_Road_Meeting_Preview']
bpy.data.objects['REFERENCE_Meeting_C63_1'].location.y=43.25
bpy.data.objects['REFERENCE_Meeting_C63_2'].location.y=45.75
report['two_cars']={'body_width_m':1.839,'mirror_width_m':2.02,'total_body_clearance_m':5-2*1.839,'total_mirror_clearance_m':5-2*2.02,'centre_mirror_gap_m':.48,'each_outer_mirror_gap_m':.24}
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2))
scene.cycles.samples=40;scene.cycles.use_denoising=True
bpy.context.preferences.filepaths.save_version=0
scene.render.image_settings.file_format='PNG'
meeting.hide_render=False;meeting.hide_viewport=False
cam=bpy.data.objects['Camera_V19_Main_Meeting_Top'];cam.name='Camera_V20_Main_Meeting_Top';cam.location.y=44.5
scene.camera=cam;scene.render.resolution_x=1500;scene.render.resolution_y=1300
scene.render.filepath=str(OUT/'main_road_5m_two_cars.png');bpy.ops.render.render(write_still=True)
meeting.hide_render=True;meeting.hide_viewport=True
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200
scene.render.filepath=str(OUT/'overview.png');bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_V16_Top'];scene.render.resolution_x=1500;scene.render.resolution_y=1500
scene.render.filepath=str(OUT/'drain_setbacks_top.png');bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_V16_Marked_Overview'];scene.render.resolution_x=1600;scene.render.resolution_y=1200
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'road_trial_v20_main5m_drain_setback.blend'))
print(json.dumps(report,indent=2))
