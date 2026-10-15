param([string]$Tool = 'run_lua', [string]$Code, [string]$ArgumentsFile)
$ErrorActionPreference = 'Stop'
$toolArguments = @{}
if ($Code) { $toolArguments.code = $Code }
if ($ArgumentsFile) { $toolArguments = Get-Content -LiteralPath $ArgumentsFile -Raw | ConvertFrom-Json -AsHashtable }
$body = @{jsonrpc='2.0';id=1;method='tools/call';params=@{name=$Tool;arguments=$toolArguments}} | ConvertTo-Json -Depth 25 -Compress
$response = Invoke-RestMethod -Uri 'http://127.0.0.1:29292/mcp' -Method Post -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 30
if ($response.error -or $response.result.isError) { throw ($response | ConvertTo-Json -Depth 25) }
foreach ($item in $response.result.content) { if ($item.type -eq 'text') { $item.text } }
