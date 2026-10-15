$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$package = Join-Path $PSScriptRoot 'package'
$asset = Join-Path $package 'art/hometown_hairpin_v3'
$zipPath = Join-Path $PSScriptRoot '../mountain_hairpin_road/beamng_hairpin_test_v3/tight_hairpin_drive_v3.zip'
$expectedHash = 'c368fef9508ffa8aba8a5b89ca79d82c998851ada262f5f1259d64dcfd7b51c4'
if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower() -ne $expectedHash) { throw 'Source ZIP differs from validated V3' }
$zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
function Read-Entry([string]$name) {
  $reader = [IO.StreamReader]::new($zip.GetEntry($name).Open())
  try { $reader.ReadToEnd() } finally { $reader.Dispose() }
}
try {
  $prefix = 'levels/tight_hairpin_drive_v3/'
  foreach ($entry in $zip.Entries) {
    if ($entry.FullName.StartsWith($prefix + 'art/')) {
      $relative = $entry.FullName.Substring(($prefix + 'art/').Length)
      $target = [IO.Path]::GetFullPath((Join-Path $asset $relative))
      if (-not $target.StartsWith([IO.Path]::GetFullPath($asset) + [IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe ZIP path' }
      New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
      [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$true)
    }
  }
  $materials = (Read-Entry ($prefix + 'main.materials.json')).Replace('/levels/tight_hairpin_drive_v3/art/', '/art/hometown_hairpin_v3/')
  [IO.File]::WriteAllText((Join-Path $asset 'main.materials.json'),$materials)
  $materialDir = Join-Path $package 'levels/gridmap_v2/art/codex_hometown_v3'
  New-Item -ItemType Directory -Path $materialDir -Force | Out-Null
  [IO.File]::WriteAllText((Join-Path $materialDir 'main.materials.json'),$materials)
  $groundDir = Join-Path $package 'levels/gridmap_v2/groundModels'
  New-Item -ItemType Directory -Path $groundDir -Force | Out-Null
  [IO.File]::WriteAllText((Join-Path $groundDir 'codex_hometown_v3.json'),(Read-Entry ($prefix + 'groundModels/hairpin_dry_concrete.json')))
  $items = (Read-Entry ($prefix + 'main/items.level.json')) -split '\r?\n' | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json -AsHashtable } | Where-Object { $_.class -eq 'TSStatic' }
  if ($items.Count -ne 10) { throw 'Expected 10 mesh objects' }
  $lines = @(@{name='HometownV3Components';class='SimGroup';groupPosition='0 0 0'} | ConvertTo-Json -Compress)
  foreach ($item in $items) {
    $item.__parent = 'HometownV3Components'
    if ($item.isRenderEnabled) { $item.Remove('isRenderEnabled') }
    $item.shapeName = $item.shapeName.Replace('/levels/tight_hairpin_drive_v3/art/', '/art/hometown_hairpin_v3/')
    $lines += $item | ConvertTo-Json -Depth 10 -Compress
    [xml]$mesh = Get-Content -LiteralPath (Join-Path $asset ('shapes/' + [IO.Path]::GetFileName($item.shapeName))) -Raw
    if ($mesh.COLLADA.asset.up_axis -ne 'Z_UP') { throw 'Unexpected mesh orientation' }
  }
  [IO.File]::WriteAllLines((Join-Path $asset 'hometown.prefab.json'),$lines)
  $sceneDir = Join-Path $package 'levels/gridmap_v2/main/MissionGroup/codex_hometown_v3'
  New-Item -ItemType Directory -Path $sceneDir -Force | Out-Null
  $scene = @{name='CodexHometownV3';class='Prefab';__parent='codex_hometown_v3';filename='/art/hometown_hairpin_v3/hometown.prefab.json';position=@(-1580,-1490,114);rotationMatrix=@(1,0,0,0,1,0,0,0,1);scale=@(1,1,1);loadMode='Automatic'}
  [IO.File]::WriteAllText((Join-Path $sceneDir 'items.level.json'),($scene | ConvertTo-Json -Compress))
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'load.lua') -Destination (Join-Path $asset 'load.lua')
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'goto_hometown.lua') -Destination (Join-Path $asset 'goto.lua')
  Write-Output 'Prepared validated V3 assets, prefab, materials, ground model, and Gridmap scene entry.'
} finally { $zip.Dispose() }
