<#
.SYNOPSIS
n8n-ops worktree manager (interactive + headless).

.DESCRIPTION
Interactive mode: choose feature (M/1/2/3/4, L, Q), then choose action (S/F/D).
Headless mode: provide -Feature and -Action parameters (no prompts).

.PARAMETER Feature
Valid values:
  M = main
  1 = f1
  2 = f2
  3 = f3
  4 = f4

.PARAMETER Action
Valid values:
  S = Start   (headless: create/prep worktree; interactive: create/prep + open window)
  F = Finish  (headless: commit only; interactive: original finish flow)
  D = Destroy (headless: destroy worktree; interactive: original destroy flow)

.PARAMETER Message
Headless Finish commit message (required for -Action F).

.PARAMETER Yes
Required for headless Destroy (explicit confirmation).

.PARAMETER AllowEmpty
Headless Finish: allow empty commit when no changes.

.PARAMETER Help
Show concise usage.

.EXAMPLE
Interactive:
  .\f.ps1

.EXAMPLE
Headless start f2:
  .\f.ps1 -Feature 2 -Action S

.EXAMPLE
Headless finish f3:
  .\f.ps1 -Feature 3 -Action F -Message "checkpoint"

.EXAMPLE
Headless destroy f4:
  .\f.ps1 -Feature 4 -Action D -Yes
#>

param(
  [ValidateSet('M','1','2','3','4')]
  [string]$Feature,
  [ValidateSet('S','F','D')]
  [string]$Action,
  [string]$Message,
  [switch]$Yes,
  [switch]$AllowEmpty,
  [switch]$Help
)

if ($Help) {
  Write-Host ""
  Write-Host "Interactive:" -ForegroundColor Cyan
  Write-Host "  Run with no parameters." -ForegroundColor Gray
  Write-Host ""
  Write-Host "Headless:" -ForegroundColor Cyan
  Write-Host "  -Feature M|1|2|3|4  -Action S|F|D" -ForegroundColor Gray
  Write-Host "  Finish requires: -Message "..."" -ForegroundColor Gray
  Write-Host "  Destroy requires: -Yes" -ForegroundColor Gray
  Write-Host ""
  exit 0
}

$RepoPath  = "F:\web\AllThings\_projects\n8n-ops.git"
$TreesPath = "F:\web\AllThings\_projects\n8n-ops-trees"
$MainPath  = "F:\web\AllThings\_projects\n8n-ops-trees\main"

# Port mapping
$PortMap = @{
    "main" = @{ Frontend = 3000; Backend = 4000 }
    "f1"   = @{ Frontend = 3001; Backend = 4001 }
    "f2"   = @{ Frontend = 3002; Backend = 4002 }
    "f3"   = @{ Frontend = 3003; Backend = 4003 }
    "f4"   = @{ Frontend = 3004; Backend = 4004 }
}

# .env files to copy from main (relative paths)
$EnvFiles = @(
    "n8n-ops-backend\.env"
    "n8n-ops-ui\.env"
)

function Copy-EnvFiles {
    param([string]$FeaturePath)
    
    foreach ($envFile in $EnvFiles) {
        $sourcePath = Join-Path $MainPath $envFile
        $destPath   = Join-Path $FeaturePath $envFile
        
        if (Test-Path $sourcePath) {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item $sourcePath $destPath -Force
            Write-Host "Copied $envFile" -ForegroundColor Gray
        } else {
            Write-Host "Warning: $envFile not found in main" -ForegroundColor Yellow
        }
    }
}

function Install-Dependencies {
    param([string]$FeaturePath)
    
    # Install Python dependencies
    $backendPath = Join-Path $FeaturePath "n8n-ops-backend"
    if (Test-Path "$backendPath\requirements.txt") {
        Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
        Push-Location $backendPath
        pip install -r requirements.txt --quiet
        Pop-Location
        Write-Host "Python dependencies installed" -ForegroundColor Gray
    }
    
    # Install Node dependencies
    $frontendPath = Join-Path $FeaturePath "n8n-ops-ui"
    if (Test-Path "$frontendPath\package.json") {
        Write-Host "Installing Node dependencies..." -ForegroundColor Cyan
        Push-Location $frontendPath
        npm install --silent
        Pop-Location
        Write-Host "Node dependencies installed" -ForegroundColor Gray
    }
}

function Start-Feature {
    param([string]$FeatureName)
    
    $FeaturePath  = "$TreesPath\$FeatureName"
    $FrontendPort = $PortMap[$FeatureName].Frontend
    $BackendPort  = $PortMap[$FeatureName].Backend

    $frontendDir = Join-Path $FeaturePath "n8n-ops-ui"
    $backendDir  = Join-Path $FeaturePath "n8n-ops-backend"

    $StartupMessage = @"
Write-Host ''
Write-Host '  =======================================' -ForegroundColor Cyan
Write-Host '  $FeatureName - n8n-ops' -ForegroundColor Cyan
Write-Host '  =======================================' -ForegroundColor Cyan
Write-Host ''
Write-Host '  Frontend: http://localhost:$FrontendPort' -ForegroundColor Green
Write-Host '  Backend:  http://localhost:$BackendPort' -ForegroundColor Green
Write-Host ''
Write-Host '  .env.local has these ports configured' -ForegroundColor Gray
Write-Host ''
Write-Host 'Starting frontend and backend as background jobs...' -ForegroundColor Cyan

Start-Job -ScriptBlock { cd '$frontendDir'; npm run dev }
Start-Job -ScriptBlock { cd '$backendDir'; python -m uvicorn app.main:app --reload --port $BackendPort }

claude --dangerously-skip-permissions
"@

    if (Test-Path $FeaturePath) {
        Write-Host "Worktree '$FeatureName' exists. Opening feature window..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FeaturePath'; $StartupMessage"
        return
    }

    # Create worktree
    Push-Location $RepoPath
    git fetch origin
    git worktree add $FeaturePath -b $FeatureName
    $wtExit = $LASTEXITCODE
    Pop-Location

    if ($wtExit -eq 0) {
        $envContent = @"
# Auto-generated by n8n-ops launcher
FEATURE_NAME=$FeatureName
FRONTEND_PORT=$FrontendPort
BACKEND_PORT=$BackendPort
PORT=$FrontendPort
API_PORT=$BackendPort
VITE_PORT=$FrontendPort
"@
        $envContent | Out-File -FilePath "$FeaturePath\.env.local" -Encoding UTF8
        
        Write-Host "Copying .env files from main..." -ForegroundColor Cyan
        Copy-EnvFiles -FeaturePath $FeaturePath
        
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        Install-Dependencies -FeaturePath $FeaturePath
        
        Write-Host "Created worktree '$FeatureName'" -ForegroundColor Green
        Write-Host "Location: $FeaturePath" -ForegroundColor Cyan
        Write-Host "Opening feature window..." -ForegroundColor Cyan

        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FeaturePath'; $StartupMessage"
    } else {
        Write-Host "Failed to create worktree" -ForegroundColor Red
    }
}

function Finish-Feature {
    param([string]$FeatureName)
    
    $FeaturePath = "$TreesPath\$FeatureName"

    if (-not (Test-Path $FeaturePath)) {
        Write-Host "Worktree '$FeatureName' not found" -ForegroundColor Red
        return
    }

    # 1) Commit feature worktree if dirty
    Write-Host ""
    Write-Host "Enter commit message for feature '$FeatureName' (or press Enter for default): " -NoNewline -ForegroundColor White
    $FeatureCommitMessage = Read-Host
    if ([string]::IsNullOrWhiteSpace($FeatureCommitMessage)) {
        $FeatureCommitMessage = "Complete feature: $FeatureName"
    }

    Write-Host "`n[1/6] Committing feature changes (if any)..." -ForegroundColor Cyan
    Push-Location $FeaturePath
    $featStatus = git status --porcelain
    if ($featStatus) {
        git add -A
        git commit -m $FeatureCommitMessage
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Commit failed in feature worktree. Fix and retry." -ForegroundColor Red
            Pop-Location
            return
        }
    } else {
        Write-Host "No pending changes in feature worktree." -ForegroundColor Gray
    }

    # 2) Push feature branch
    Write-Host "`n[2/6] Pushing feature branch..." -ForegroundColor Cyan
    git push -u origin $FeatureName 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push of feature branch failed. Check git output above." -ForegroundColor Red
        Pop-Location
        return
    }
    Pop-Location

    # 3) Ensure main is clean: if dirty, commit first
    Write-Host "`n[3/6] Ensuring main is clean before merge..." -ForegroundColor Cyan
    Push-Location $MainPath
    $mainStatus = git status --porcelain

    if ($mainStatus) {
        Write-Host "Main has pending changes:" -ForegroundColor Yellow
        git status -sb

        Write-Host ""
        Write-Host "Enter commit message for main (or press Enter for default): " -NoNewline -ForegroundColor White
        $MainCommitMessage = Read-Host
        if ([string]::IsNullOrWhiteSpace($MainCommitMessage)) {
            $MainCommitMessage = "Pre-merge main cleanup"
        }

        git add -A
        git commit -m $MainCommitMessage
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Commit failed on main. Fix and rerun Finish-Feature." -ForegroundColor Red
            Pop-Location
            return
        }
    } else {
        Write-Host "Main is clean. No pre-merge commit needed." -ForegroundColor Gray
    }

    # 4) Merge feature into main
    Write-Host "`n[4/6] Pulling and merging '$FeatureName' into main..." -ForegroundColor Cyan
    git pull
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git pull failed on main. Fix this and rerun Finish-Feature." -ForegroundColor Red
        Pop-Location
        return
    }

    git merge $FeatureName -m "Merge feature: $FeatureName"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nMerge conflict detected!" -ForegroundColor Red
        Write-Host "Resolve conflicts in: $MainPath" -ForegroundColor Yellow
        Write-Host "Then commit and run finish again" -ForegroundColor Yellow
        Pop-Location
        return
    }

    git push
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed on main. Check git output above." -ForegroundColor Red
        Pop-Location
        return
    }
    Pop-Location

    # 5) Remove worktree and branches
    Write-Host "`n[5/6] Removing worktree and branches..." -ForegroundColor Cyan
    Push-Location $RepoPath
    git worktree remove $FeaturePath --force
    git branch -d $FeatureName 2>$null
    git push origin --delete $FeatureName 2>$null
    git worktree prune
    Pop-Location

    # 6) Done
    Write-Host "`n[6/6] Complete!" -ForegroundColor Green
    Write-Host "Feature '$FeatureName' merged and cleaned up." -ForegroundColor Green
}

function Commit-Main {
    if (-not (Test-Path $MainPath)) {
        Write-Host "Main worktree not found at $MainPath" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "[1/3] Checking main status..." -ForegroundColor Cyan
    Push-Location $MainPath
    $status = git status --porcelain

    if (-not $status) {
        Write-Host "No changes to commit on main." -ForegroundColor Gray
        Pop-Location
        return
    }

    git status -sb

    Write-Host ""
    Write-Host "Enter commit message (or press Enter for default): " -NoNewline -ForegroundColor White
    $CommitMessage = Read-Host
    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        $CommitMessage = "Update main"
    }

    Write-Host "`n[2/3] Committing changes..." -ForegroundColor Cyan
    git add -A
    git commit -m $CommitMessage

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit failed. Check git output above." -ForegroundColor Red
        Pop-Location
        return
    }

    Write-Host "`n[3/3] Pushing main..." -ForegroundColor Cyan
    git push

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed. Check git output above." -ForegroundColor Red
        Pop-Location
        return
    }

    Pop-Location
    Write-Host "`nMain branch committed and pushed." -ForegroundColor Green
}

function Destroy-Feature {
    param([string]$FeatureName)
    
    $FeaturePath = "$TreesPath\$FeatureName"

    if (-not (Test-Path $FeaturePath)) {
        Write-Host "Worktree '$FeatureName' not found" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "WARNING: This will destroy '$FeatureName' without merging!" -ForegroundColor Red
    Write-Host "Type 'yes' to confirm: " -NoNewline -ForegroundColor Yellow
    $confirm = Read-Host
    
    if ($confirm -ne "yes") {
        Write-Host "Cancelled" -ForegroundColor Gray
        return
    }

    Write-Host "`nKilling processes..." -ForegroundColor Cyan
    taskkill /F /IM python.exe 2>$null | Out-Null
    taskkill /F /IM node.exe 2>$null | Out-Null
    Start-Sleep -Seconds 1

    Write-Host "Removing folder..." -ForegroundColor Cyan
    Remove-Item -Path $FeaturePath -Recurse -Force -ErrorAction SilentlyContinue
    
    if (Test-Path $FeaturePath) {
        Write-Host "Folder still locked. Try closing all windows and run destroy again." -ForegroundColor Red
        return
    }

    Write-Host "Cleaning up git..." -ForegroundColor Cyan
    Push-Location $RepoPath
    git worktree prune
    git branch -D $FeatureName 2>$null
    git push origin --delete $FeatureName 2>$null
    Pop-Location

    Write-Host "`nDestroyed '$FeatureName'" -ForegroundColor Green
}

function List-Worktrees {
    Write-Host ""
    Write-Host "Active Worktrees:" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Cyan
    Push-Location $RepoPath
    git worktree list
    Pop-Location
}


# ---------- New Menus ----------
$FeatureOrder = @("M","1","2","3","4")
$FeatureKeyToName = @{
  "M" = "main"
  "1" = "f1"
  "2" = "f2"
  "3" = "f3"
  "4" = "f4"
}

function Test-FeatureExists {
  param([string]$FeatureName)
  Test-Path "$TreesPath\$FeatureName"
}

function Show-FeatureMenu {
  Clear-Host
  Write-Host ""
  Write-Host "  n8n-ops Feature Manager" -ForegroundColor Cyan
  Write-Host "  =======================" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "  Key  Feature  Exists" -ForegroundColor White
  Write-Host "  ---  -------  ------" -ForegroundColor Gray

  foreach ($k in $FeatureOrder) {
    $n = $FeatureKeyToName[$k]
    $exists = if (Test-FeatureExists $n) { "Yes" } else { "No" }
    Write-Host ("   {0,-2}  {1,-7} {2}" -f $k, $n, $exists)
  }

  Write-Host ""
  Write-Host "   L   List"
  Write-Host "   Q   Quit"
  Write-Host ""
}

function Show-ActionMenu {
  param([string]$FeatureName)

  $exists = Test-FeatureExists $FeatureName

  Clear-Host
  Write-Host "Feature: $FeatureName   Exists: $(if ($exists) { 'Yes' } else { 'No' })"
  Write-Host ""
  Write-Host "Select ACTION:"
  Write-Host "  S  Start"

  # Finish is practically available only if feature exists
  if ($exists) { Write-Host "  F  Finish" }

  # Destroy is practically available only if feature exists and not main
  if ($exists -and $FeatureName -ne "main") { Write-Host "  D  Destroy" }

  Write-Host "  B  Back"
  Write-Host "  Q  Quit"
  Write-Host ""
}

# ---------- Headless adapters ----------
function Start-FeatureHeadless {
  param([string]$FeatureName)

  # Use the original Start-Feature creation/prep, but do NOT open a new window.
  # This mirrors the "this all worked" behavior, minus UI.
  $FeaturePath  = "$TreesPath\$FeatureName"
  $FrontendPort = $PortMap[$FeatureName].Frontend
  $BackendPort  = $PortMap[$FeatureName].Backend

  if (Test-Path $FeaturePath) { return }

  # 1) Create worktree (original behavior)
  Push-Location $RepoPath
  git fetch origin
  git worktree add $FeaturePath -b $FeatureName
  $wtExit = $LASTEXITCODE
  Pop-Location

  if ($wtExit -ne 0) { throw "Failed to create worktree '$FeatureName' (git worktree add exit $wtExit)" }

  # 2) Create .env.local (original behavior)
  $envContent = @"
FRONTEND_PORT=$FrontendPort
BACKEND_PORT=$BackendPort
PORT=$FrontendPort
API_PORT=$BackendPort
VITE_PORT=$FrontendPort
"@
  $envContent | Out-File -FilePath "$FeaturePath\.env.local" -Encoding UTF8

  # 3) Copy env files + install deps (original behavior)
  Copy-EnvFiles -FeaturePath $FeaturePath
  Install-Dependencies -FeaturePath $FeaturePath
}

function Finish-FeatureHeadless {
  param([string]$FeatureName, [string]$CommitMessage, [switch]$AllowEmpty)

  $FeaturePath = "$TreesPath\$FeatureName"
  if (-not (Test-Path $FeaturePath)) { throw "Worktree '$FeatureName' not found." }

  Push-Location $FeaturePath
  try {
    git add -A
    $hasChanges = -not [string]::IsNullOrWhiteSpace((git status --porcelain))
    if (-not $hasChanges -and -not $AllowEmpty) { throw "No changes to commit." }

    if (-not $hasChanges -and $AllowEmpty) {
      git commit --allow-empty -m $CommitMessage
    } else {
      git commit -m $CommitMessage
    }
    if ($LASTEXITCODE -ne 0) { throw "Commit failed." }
  }
  finally {
    Pop-Location
  }
}

function Destroy-FeatureHeadless {
  param([string]$FeatureName)

  if ($FeatureName -eq "main") { throw "Refusing to destroy 'main'." }
  Destroy-Feature $FeatureName
}

# ---------- Headless Mode ----------
if ($Feature -or $Action) {
  if (-not ($Feature -and $Action)) { Write-Error "Headless mode requires both -Feature and -Action."; exit 1 }

  $featureName = $FeatureKeyToName[$Feature.ToUpper()]
  if (-not $featureName) { Write-Error "Invalid -Feature."; exit 1 }

  try {
    switch ($Action.ToUpper()) {
      "S" { Start-FeatureHeadless -FeatureName $featureName; exit 0 }
      "F" {
        if (-not $Message) { Write-Error "-Message is required for headless Finish."; exit 1 }
        Finish-FeatureHeadless -FeatureName $featureName -CommitMessage $Message -AllowEmpty:$AllowEmpty
        exit 0
      }
      "D" {
        if (-not $Yes) { Write-Error "-Yes is required for headless Destroy."; exit 1 }
        Destroy-FeatureHeadless -FeatureName $featureName
        exit 0
      }
      default { Write-Error "Invalid -Action."; exit 1 }
    }
  }
  catch {
    Write-Error $_
    exit 1
  }
}

# ---------- Interactive Loop (new flow) ----------
while ($true) {
  Show-FeatureMenu
  $k = (Read-Host "  Select").Trim().ToUpper()

  if ($k -eq "Q") { exit }
  if ($k -eq "L") { List-Worktrees; pause; continue }
  if (-not $FeatureKeyToName.ContainsKey($k)) { continue }

  $featureName = $FeatureKeyToName[$k]

  while ($true) {
    Show-ActionMenu $featureName
    $a = (Read-Host "  Action").Trim().ToUpper()

    if ($a -eq "Q") { exit }
    if ($a -eq "B") { break }

    switch ($a) {
      "S" { Start-Feature $featureName; break }  # original Start-Feature (opens window) - this all worked
      "F" { 
        if (Test-FeatureExists $featureName) { Finish-Feature $featureName }
        break
      }
      "D" {
        if (Test-FeatureExists $featureName -and $featureName -ne "main") { Destroy-Feature $featureName }
        break
      }
      default { continue }
    }
  }
}
