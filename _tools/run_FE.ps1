cls

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontEndDir = Join-Path $ScriptDir "..\app-front\scripts"

Set-Location $FrontEndDir
npm run dev
