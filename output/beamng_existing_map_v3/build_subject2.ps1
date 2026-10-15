$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '../china_subject2/beamng_v1/package/levels/china_c1_subject2_v1'
$zipPath = Join-Path $PSScriptRoot '../china_subject2/beamng_v1/china_c1_subject2_v1.zip'
if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower() -ne 'f467aa3afe41b885a9758500a5708311ba219ba917bc76c4545eccc27ceca7d3') { throw 'Unexpected Subject 2 ZIP hash' }
$package = Join-Path $PSScriptRoot 'package'
$asset = Join-Path $package 'art/china_subject2_v1'
New-Item -ItemType Directory -Path $asset -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'art/shapes') -Destination $asset -Recurse -Force
Copy-Item -LiteralPath (Join-Path $source 'art/textures') -Destination $asset -Recurse -Force
$materials = (Get-Content -LiteralPath (Join-Path $source 'main.materials.json') -Raw).Replace('/levels/china_c1_subject2_v1/art/', '/art/china_subject2_v1/')
[IO.File]::WriteAllText((Join-Path $asset 'main.materials.json'),$materials)
$materialDir = Join-Path $package 'levels/gridmap_v2/art/codex_subject2_v1'
New-Item -ItemType Directory -Path $materialDir -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $materialDir 'main.materials.json'),$materials)
$groundDir = Join-Path $package 'levels/gridmap_v2/groundModels'
New-Item -ItemType Directory -Path $groundDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'groundModels/c1_dry_concrete.json') -Destination (Join-Path $groundDir 'codex_subject2_v1.json')
$items = Get-Content -LiteralPath (Join-Path $source 'main/MissionGroup/items.level.json') | ForEach-Object { $_ | ConvertFrom-Json -AsHashtable } | Where-Object { $_.class -eq 'TSStatic' }
if ($items.Count -ne 22) { throw 'Expected 22 Subject 2 objects' }
$lines = @(@{name='Subject2V1Components';class='SimGroup';groupPosition='0 0 0'} | ConvertTo-Json -Compress)
foreach ($item in $items) {
  $item.__parent = 'Subject2V1Components'
  $item.Remove('isRenderEnabled')
  # BeamNG 0.39 ignores these zero-thickness planes in Collision Mesh mode.
  # Visible Mesh Final uses exactly the same approved road surface geometry.
  if ($item.name -in @('c1_road_flat_asphalt','c1_road_flat_concrete')) {
    $item.collisionType = 'Visible Mesh Final'
    $item.decalType = 'Visible Mesh Final'
  }
  $item.shapeName = $item.shapeName.Replace('/levels/china_c1_subject2_v1/art/', '/art/china_subject2_v1/')
  $lines += $item | ConvertTo-Json -Depth 10 -Compress
}
[IO.File]::WriteAllLines((Join-Path $asset 'subject2.prefab.json'),$lines)
$sceneDir = Join-Path $package 'levels/gridmap_v2/main/MissionGroup/codex_subject2_v1'
New-Item -ItemType Directory -Path $sceneDir -Force | Out-Null
$scene = @{name='CodexSubject2V1';class='Prefab';__parent='codex_subject2_v1';filename='/art/china_subject2_v1/subject2.prefab.json';position=@(-1700,-1500,101);rotationMatrix=@(1,0,0,0,1,0,0,0,1);scale=@(1,1,1);loadMode='Automatic'}
[IO.File]::WriteAllText((Join-Path $sceneDir 'items.level.json'),($scene | ConvertTo-Json -Compress))
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'load_subject2.lua') -Destination (Join-Path $asset 'load.lua')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'goto_subject2.lua') -Destination (Join-Path $asset 'goto.lua')
Write-Output 'Prepared Subject 2 V07 / BeamNG V1: 13 meshes, 22 objects.'
