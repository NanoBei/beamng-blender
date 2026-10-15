$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$liveRoot = 'C:/Users/yangc/AppData/Local/BeamNG/BeamNG.drive/current/levels/gridmap_v2/main/MissionGroup/items.level.json'
$backup = Join-Path $PSScriptRoot 'backup'
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$snapshot = Join-Path $backup 'original_mission_items.level.json'
if (-not (Test-Path -LiteralPath $snapshot)) {
  if (Test-Path -LiteralPath $liveRoot) { Copy-Item -LiteralPath $liveRoot -Destination $snapshot }
  else {
    $z = [IO.Compression.ZipFile]::OpenRead('D:/Steam/steamapps/common/BeamNG.drive/content/levels/gridmap_v2.zip')
    try {
      $r = [IO.StreamReader]::new($z.GetEntry('levels/gridmap_v2/main/MissionGroup/items.level.json').Open())
      try { [IO.File]::WriteAllText($snapshot,$r.ReadToEnd()) } finally { $r.Dispose() }
    } finally { $z.Dispose() }
  }
}
$text = Get-Content -LiteralPath $snapshot -Raw
foreach ($name in @('codex_hometown_v3','codex_subject2_v1')) {
  if ($text.Contains('"name":"' + $name + '"')) { throw 'Group already exists in baseline' }
  $text += "`n" + (@{class='SimGroup';name=$name;__parent='MissionGroup'} | ConvertTo-Json -Compress)
}
$out = Join-Path $PSScriptRoot 'package/levels/gridmap_v2/main/MissionGroup/items.level.json'
[IO.File]::WriteAllText($out,$text+"`n")
Write-Output 'Preserved original MissionGroup entries and registered two additional scene groups.'
