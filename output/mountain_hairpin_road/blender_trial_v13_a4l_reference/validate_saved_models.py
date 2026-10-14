"""Read back both delivered .blend files; verify their actual evaluated geometry."""
import bpy, json
from pathlib import Path
from mathutils import Vector

out=Path(__file__).resolve().parent
results={}
for filename,location in [('road_trial_v13_a4l_reference.blend',(7.5,44.25,0)),
                          ('audi_a4l_reference_asset.blend',(0,0,0))]:
    bpy.ops.wm.open_mainfile(filepath=str(out/filename))
    scene=bpy.data.scenes.get('Audi_A4L_Reference_Only') or bpy.context.scene
    if bpy.context.window: bpy.context.window.scene=scene
    collection=bpy.data.collections['REFERENCE_Audi_A4L_EXCLUDE_FROM_MAP']
    root=next(o for o in collection.objects if o.type=='EMPTY')
    assert (root.location-Vector(location)).length<1e-6
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    points=[];contacts={};axles={};triangles=0
    for o in collection.objects:
        if o.type not in {'MESH','CURVE','FONT'}:continue
        e=o.evaluated_get(deps);m=e.to_mesh();m.calc_loop_triangles()
        triangles+=len(m.loop_triangles)
        pts=[root.matrix_world.inverted() @ e.matrix_world @ v.co for v in m.vertices]
        if not o.get('mirror_part'):points.extend(pts)
        if o.type=='MESH' and 'axle_center_x_m' in o:
            contacts[o.name]=min(p.z for p in pts)
            axles[o.name]=(min(p.x for p in pts)+max(p.x for p in pts))/2
        e.to_mesh_clear()
    size=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
    wb=max(axles.values())-min(axles.values())
    assert all(abs(a-b)<.00005 for a,b in zip(size,(4.858,1.847,1.439))),size
    assert abs(wb-2.908)<.00005,wb
    assert len(contacts)==4 and all(abs(z)<.00005 for z in contacts.values()),contacts
    road_count=sum(o.name.startswith('Road_Surface_') for o in scene.objects)
    assert road_count==(2 if filename.startswith('road_') else 0),road_count
    results[filename]={'scene':scene.name,'location':list(root.location),
        'actual_body_dimensions_m':size,'actual_wheelbase_m':wb,'tyre_ground_heights_m':contacts,
        'road_objects':road_count,'car_evaluated_triangles':triangles,'passed':True}
(out/'saved_file_validation.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
