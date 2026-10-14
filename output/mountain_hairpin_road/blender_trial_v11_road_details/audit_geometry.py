"""Measure saved V11 geometry independently of its dimension metadata."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT=Path(__file__).resolve().parent
road=bpy.data.objects['Road_Surface_Small_Concrete_2p7705m']
verts=[v.co.copy() for v in road.data.vertices]
counts={}
for face in road.data.polygons:
    indices=list(face.vertices)
    for a,b in zip(indices,indices[1:]+indices[:1]):
        edge=tuple(sorted((a,b)));counts[edge]=counts.get(edge,0)+1
edges=[e for e,count in counts.items() if count==1]
# Mid-sections of the three straights, away from the junction and corner fills.
sections=[((11,44),-25,12),((28.631327,31.789041),-170,6),((16.813635,25.790652),-25,8)]
widths=[]
for origin,deg,distance in sections:
    angle=math.radians(deg);t=Vector((math.cos(angle),math.sin(angle)))
    n=Vector((-t.y,t.x));c=Vector(origin)+t*distance
    offsets=[]
    for a,b in edges:
        p=Vector(verts[a][:2]);q=Vector(verts[b][:2])
        dp=(p-c).dot(t);dq=(q-c).dot(t)
        if dp*dq<=0 and abs(dp-dq)>1e-10:
            hit=p+(q-p)*(dp/(dp-dq));offset=(hit-c).dot(n)
            if abs(offset)<2:offsets.append(offset)
    left=min(v for v in offsets if v>0);right=max(v for v in offsets if v<0)
    widths.append(left-right)
    assert abs(left-right-2.7705)<.0001,(origin,offsets)

main=bpy.data.objects['Road_Surface_Main_Asphalt_4p5m']
main_width=max(v.co.y for v in main.data.vertices)-min(v.co.y for v in main.data.vertices)
main_bvh=BVHTree.FromPolygons([v.co.copy() for v in main.data.vertices],[list(p.vertices) for p in main.data.polygons])
support=[]
for x in [7.5-1.386,7.5+1.522]:
    for y in [44.25-.792,44.25+.792]:
        hit=main_bvh.ray_cast(Vector((x,y,5)),Vector((0,0,-1)),10)[0]
        assert hit is not None and abs(hit.z)<1e-6
        support.append(list(hit))
ditch=bpy.data.objects['Drainage_Channel_Clear_0p50m_Deep_0p60m']
bvh=BVHTree.FromPolygons([v.co.copy() for v in ditch.data.vertices],[list(p.vertices) for p in ditch.data.polygons])
channel_samples=[]
for y,z in [(46.55,0),(46.63,-.6),(46.87,-.6),(47.11,-.6),(47.2,0)]:
    hit=bvh.ray_cast(Vector((22,y,5)),Vector((0,0,-1)),10)[0]
    assert hit is not None and abs(hit.z-z)<1e-5,(y,hit)
    channel_samples.append(list(hit))
assert main_width==4.5
report={'main_measured_width_m':main_width,'small_measured_cross_section_widths_m':widths,
        'car_four_wheel_ground_points_m':support,'ditch_open_top_and_floor_ray_hits_m':channel_samples,
        'beamng_runtime_tested':False}
(OUT/'geometry_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
