from pathlib import Path
D=Path(__file__).resolve().parent
p=D/'build.py'
s=p.read_text().replace('codex_connected_v3_innerfill','codex_connected_v4_innerfill_more').replace('CodexConnectedV3Innerfill','CodexConnectedV4InnerfillMore')
s=s.replace('amount=1.2*','amount=1.8*')
s=s.replace("x.get('name')!='codex_connected_v2_width130'", "x.get('name') not in ('codex_connected_v2_width130','codex_connected_v3_innerfill')")
s=s.replace("local old=scenetree.findObject('CodexConnectedV2Width130')", "local old=scenetree.findObject('CodexConnectedV3Innerfill')")
s=s.replace('tip_after=new[tip].tolist()', 'tip_after_xy=new[tip,:2].tolist()').replace(',seam_height_error_m=0','')
p.write_text(s)
p=D/'trim_terrain.py'
s=p.read_text().replace("D/'.deps'", "ROOT/'output/connected_maps_v3_innerfill/.deps'").replace('codex_connected_v3_innerfill','codex_connected_v4_innerfill_more')
p.write_text(s)
p=D/'check_fill.py'
s=p.read_text().replace('from drive_check import lua', "import sys\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/'connected_maps_v3_innerfill'))\nfrom drive_check import lua")
p.write_text(s)
