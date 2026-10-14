"""Independently reopen delivered models and measure evaluated world geometry."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
results={}
for filename,pos in [('road_trial_v14_c63_reference.blend',(7.5,44.25,0)),('mercedes_amg_c63_reference.blend',(0,0,0))]:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/filename))
    scene=bpy.context.scene;coll=bpy.data.collections['REFERENCE_Mercedes_AMG_C63_EXCLUDE_FROM_MAP']
    root=next(o for o in coll.objects if o.type=='EMPTY')
    assert (root.location-Vector(pos)).length<1e-6
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    allp=[];bodyp=[];wheels={};tris=0
    for o in coll.objects:
        if o.type!='MESH':continue
        assert not o.animation_data and not o.constraints and not o.modifiers
        e=o.evaluated_get(deps);me=e.to_mesh();me.calc_loop_triangles();tris+=len(me.loop_triangles)
        p=np.array([e.matrix_world@v.co for v in me.vertices]);allp.append(p)
        a=me.attributes.get('exclude_from_body_width')
        mask=np.array([not v.value for v in a.data]) if a else np.ones(len(p),dtype=bool)
        bodyp.append(p[mask])
        if o.get('axle'):
            lo=p.min(0);hi=p.max(0);mid=(lo+hi)/2
            wheels[o.name]={'center_world':mid.tolist(),'lowest_z_m':float(lo[2]),'axle':o['axle']}
            assert abs(lo[2])<.00005
            if filename.startswith('road_'):
                hit,where,*_=scene.ray_cast(deps,Vector((mid[0],mid[1],-.001)),Vector((0,0,-1)))
                # Main road Solidify has a 0.1 m underside; check the actual top separately.
                road=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m']
                ok,point,_,_=road.ray_cast(Vector((mid[0],mid[1],1)),Vector((0,0,-1)))
                assert ok and abs(point.z)<.00005
        e.to_mesh_clear()
    p=np.concatenate(allp);bp=np.concatenate(bodyp)
    span=np.ptp(p,axis=0);body_width=np.ptp(bp[:,1])
    axle={a:np.mean([w['center_world'][0] for w in wheels.values() if w['axle']==a]) for a in ['front','rear']}
    wb=axle['front']-axle['rear']
    assert np.allclose([span[0],body_width,span[1],span[2],wb],[4.756,1.839,2.02,1.426,2.84],atol=.00005)
    assert len(wheels)==4
    assert not any(o.name.startswith('A4L13_') for o in scene.objects)
    road_count=sum(o.name.startswith('Road_Surface_') for o in scene.objects)
    assert road_count==(2 if filename.startswith('road_') else 0)
    missing=[i.filepath for i in bpy.data.images if i.source=='FILE' and i.users and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
    assert not missing,missing
    results[filename]={'passed':True,'world_position_m':list(root.location),'length_m':float(span[0]),'body_width_m':float(body_width),
      'including_mirrors_width_m':float(span[1]),'height_m':float(span[2]),'wheelbase_m':float(wb),'wheel_checks':wheels,
      'car_mesh_triangles':tris,'road_object_count':road_count,'missing_used_textures':missing}
(OUT/'saved_file_validation.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
