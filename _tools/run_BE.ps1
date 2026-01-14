# pip install -r requirements.txt
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$PythonScript = Join-Path $ScriptDir `
    "..\app-back\scripts\start_with_migrations.py"

python $PythonScript
