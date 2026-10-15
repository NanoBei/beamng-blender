$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$assetRoot = Join-Path $PSScriptRoot 'package/art/hairpin_road'
New-Item -ItemType Directory -Path $assetRoot -Force | Out-Null
$archive = [IO.Compression.ZipFile]::OpenRead((Join-Path $PSScriptRoot '../beamng_hairpin_test_v1/tight_hairpin_test_v1.zip'))
try {
  foreach ($entry in $archive.Entries) {
    $prefix = 'levels/tight_hairpin_test/art/'
    if ($entry.FullName.StartsWith($prefix)) {
      $target = Join-Path $assetRoot $entry.FullName.Substring($prefix.Length)
      New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
      [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
    }
  }
  $reader = [IO.StreamReader]::new($archive.GetEntry('levels/tight_hairpin_test/main.materials.json').Open())
  try { $materials = $reader.ReadToEnd().Replace('/levels/tight_hairpin_test/art/', '/art/hairpin_road/') } finally { $reader.Dispose() }
  [IO.File]::WriteAllText((Join-Path $assetRoot 'main.materials.json'), $materials)
} finally { $archive.Dispose() }
$lines = @(@{name='HairpinRoadComponents';class='SimGroup';groupPosition='0 0 0'} | ConvertTo-Json -Compress)
foreach ($part in @('road','terrain','earth_sides','guardrails')) {
  $lines += @{name="hairpin_$part";class='TSStatic';__parent='HairpinRoadComponents';shapeName="/art/hairpin_road/shapes/$part.dae";position=@(0,0,0);rotationMatrix=@(1,0,0,0,1,0,0,0,1);scale=@(1,1,1);collisionType='Visible Mesh Final';decalType='Visible Mesh Final'} | ConvertTo-Json -Compress
  [xml]$mesh = Get-Content -LiteralPath (Join-Path $assetRoot "shapes/$part.dae") -Raw
  if ($mesh.COLLADA.version -ne '1.4.1') { throw "Unexpected COLLADA version for $part" }
}
[IO.File]::WriteAllLines((Join-Path $assetRoot 'hairpin.prefab.json'), $lines)
Write-Output "Built and XML-validated four meshes at $assetRoot"
