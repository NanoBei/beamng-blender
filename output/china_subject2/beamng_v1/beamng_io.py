"""Minimal Collada 1.4.1 writer with BeamNG render/LOD/collision hierarchy.
Inputs are already triangulated world-space meshes. No Blender API dependency.
"""
import xml.etree.ElementTree as ET
from collections import defaultdict
NS='http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('',NS)
def el(parent,tag,text=None,**attrs):
    n=ET.SubElement(parent,'{'+NS+'}'+tag,{k:str(v) for k,v in attrs.items()})
    if text is not None:n.text=text
    return n
def floats(v):return ' '.join(format(float(x),'.9g') for x in v)
def write_dae(path,asset_name,levels,collision,materials):
    root=ET.Element('{'+NS+'}COLLADA',version='1.4.1')
    a=el(root,'asset');c=el(a,'contributor');el(c,'authoring_tool','C1 V07 / BeamNG 0.39 export V1')
    el(a,'created','2026-10-14T00:00:00Z');el(a,'modified','2026-10-14T00:00:00Z')
    el(a,'unit',name='meter',meter=1);el(a,'up_axis','Z_UP')
    effects=el(root,'library_effects');mats=el(root,'library_materials')
    used=set(t[3] for meshes in levels.values() for t in meshes)
    used.update(t[3] for t in collision)
    for name in sorted(used):
        fx=el(effects,'effect',id=name+'-fx');tech=el(el(fx,'profile_COMMON'),'technique',sid='common')
        diff=el(el(tech,'lambert'),'diffuse');el(diff,'color',floats(materials[name]['color']))
        m=el(mats,'material',id=name,name=name);el(m,'instance_effect',url='#'+name+'-fx')
    geoms=el(root,'library_geometries');vs=el(el(root,'library_visual_scenes'),'visual_scene',id='Scene',name='Scene')
    base=el(vs,'node',id='base00',name='base00',type='NODE')
    start=el(base,'node',id='start01',name='start01',type='NODE')
    stats=[]
    def emit(tris,label,role,lod):
        # Deindex corners to keep normals and UVs unambiguous; cap below 65535.
        for chunk,offset in enumerate(range(0,len(tris),18000)):
            block=tris[offset:offset+18000]
            node_name=(f'Colmesh_{asset_name}_{chunk}-1' if role=='collision' else f'{asset_name}_{chunk}_L{lod}')
            gid=f'{label}_{chunk}_geometry';gm=el(geoms,'geometry',id=gid,name=node_name);mesh=el(gm,'mesh')
            def source(suffix,values,components):
                sid=gid+'_'+suffix;s=el(mesh,'source',id=sid)
                el(s,'float_array',floats(values),id=sid+'_array',count=len(values))
                acc=el(el(s,'technique_common'),'accessor',source='#'+sid+'_array',count=len(values)//len(components),stride=len(components))
                for n in components:el(acc,'param',name=n,type='float')
                return sid
            pos=source('p',[x for t in block for v in t[0] for x in v],['X','Y','Z'])
            norm=source('n',[x for t in block for v in t[1] for x in v],['X','Y','Z'])
            uv=source('uv',[x for t in block for v in t[2] for x in v],['S','T'])
            vert=el(mesh,'vertices',id=gid+'_vertices');el(vert,'input',semantic='POSITION',source='#'+pos)
            groups=defaultdict(list)
            for i,t in enumerate(block):groups[t[3]].extend(range(i*3,i*3+3))
            for mat,ix in sorted(groups.items()):
                tr=el(mesh,'triangles',material=mat,count=len(ix)//3)
                for sem,src,offset in [('VERTEX',gid+'_vertices',0),('NORMAL',norm,1),('TEXCOORD',uv,2)]:
                    attrs={'semantic':sem,'source':'#'+src,'offset':offset}
                    if sem=='TEXCOORD':attrs['set']=0
                    el(tr,'input',**attrs)
                el(tr,'p',' '.join(str(i) for j in ix for i in (j,j,j)))
            node=el(start,'node',id=node_name,name=node_name,type='NODE')
            inst=el(node,'instance_geometry',url='#'+gid)
            bind=el(el(inst,'bind_material'),'technique_common')
            for mat in sorted(groups):
                mi=el(bind,'instance_material',symbol=mat,target='#'+mat)
                el(mi,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set=0)
            stats.append({'node':node_name,'role':role,'lod':lod,'triangles':len(block),'vertices':len(block)*3})
    for lod,tris in sorted(levels.items(),reverse=True):
        el(base,'node',id=f'detail{lod}',name=f'detail{lod}',type='NODE')
        emit(tris,f'{asset_name}_L{lod}','render',lod)
    if collision:
        el(base,'node',id='collision-1',name='collision-1',type='NODE')
        emit(collision,asset_name+'_collision','collision',-1)
    el(el(root,'scene'),'instance_visual_scene',url='#Scene')
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    return stats
