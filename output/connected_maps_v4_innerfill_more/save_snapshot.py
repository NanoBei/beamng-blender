"""Verify persisted V4 and preserve its installed dependencies for restoration."""
from pathlib import Path
import hashlib,json,zipfile
D=Path(__file__).resolve().parent
USER=Path('C:/Users/yangc/AppData/Local/BeamNG/BeamNG.drive/current')
level=Path('levels/gridmap_v2/main/MissionGroup')
group='codex_connected_v4_innerfill_more'
root=[json.loads(s) for s in (USER/level/'items.level.json').read_text(encoding='utf-8-sig').splitlines()]
assert any(x.get('name')==group for x in root)
assert not any(x.get('name') in ['codex_connected_v3_innerfill','codex_connected_v2_width130'] for x in root)
registration=json.loads((USER/level/group/'items.level.json').read_text())
assert registration['loadMode']=='Automatic'
prefab=USER/registration['filename'].lstrip('/')
objects=[json.loads(s) for s in prefab.read_text().splitlines()]
assert all((USER/x['shapeName'].lstrip('/')).is_file() for x in objects if 'shapeName' in x)
verified=0
for p in (D/'package').rglob('*'):
    if p.is_file() and p.suffix!='.cdae':
        installed=USER/p.relative_to(D/'package')
        assert installed.is_file() and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(installed.read_bytes()).digest(),str(p)
        verified+=1
folders={Path(*Path(x['shapeName'].lstrip('/')).parts[:2]) for x in objects if 'shapeName' in x}
folders.add(Path('art/hometown_hairpin_v3'))
files=[USER/level/'items.level.json',USER/level/group/'items.level.json']
for folder in sorted(folders):
    files.extend(p for p in (USER/folder).rglob('*') if p.is_file() and p.suffix!='.cdae')
archive=D/'双地图_V4_已保存备份.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(USER).as_posix())
    z.writestr('恢复说明.txt','这是当前 Gridmap V2 双地图扩展的用户目录备份，依赖游戏自带 Gridmap V2。\n正常使用无需解压：游戏内自由驾驶选择 Gridmap V2 即可。\n仅需恢复时：退出游戏，将 art 和 levels 文件夹合并至 BeamNG 用户目录 current；先备份该目录现有同名文件。\n')
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
report=dict(automatic_load=True,verified_package_files=verified,referenced_shapes=sum('shapeName' in x for x in objects),backup_files=len(files),backup=str(archive),backup_bytes=archive.stat().st_size)
(D/'save_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
