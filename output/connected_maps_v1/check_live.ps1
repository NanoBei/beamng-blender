param([switch]$Before)
$ErrorActionPreference='Stop'
$json=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'collision_probes.json') -Raw
$code=@'
local samples=jsonDecode([==[PAYLOAD]==]);local failed={};local obstructed={};local maxError=0
for _,p in ipairs(samples) do
  local h=180-castRayStatic(vec3(p.x,p.y,180),vec3(0,0,-1),100)
  local e=math.abs(h-p.z);maxError=math.max(maxError,e)
  if e>.035 then failed[#failed+1]={route=p.route,s=p.s,x=p.x,y=p.y,expected=p.z,actual=h,error=e} end
  if h-p.z>.035 then obstructed[#obstructed+1]={route=p.route,s=p.s,x=p.x,y=p.y,expected=p.z,actual=h} end
end
return jsonEncode({samples=#samples,failCount=#failed,obstructionCount=#obstructed,failed=failed,obstructed=obstructed,maxError=maxError})
'@
$result=& (Join-Path $PSScriptRoot '../beamng_existing_map/mcp.ps1') -Code ($code.Replace('PAYLOAD',$json))
$name=if($Before){'before_connection_checks.json'}else{'live_connection_checks.json'}
$result | Set-Content -LiteralPath (Join-Path $PSScriptRoot $name) -Encoding utf8
$r=$result | ConvertFrom-Json
@{samples=$r.samples;failures=$r.failCount;obstructions=$r.obstructionCount;maxError=$r.maxError} | ConvertTo-Json
if($Before){$r.obstructed | Select-Object -First 8 | ConvertTo-Json -Depth 5}else{$r.failed | Select-Object -First 8 | ConvertTo-Json -Depth 5}
