# =====================================
# Worktree Menu – Option A (Refined)
# =====================================

$WorktreeRoot = "F:\web\AllThings\_projects\n8n-ops-trees"

$FeatureOrder = @("M", "1", "2", "3", "4")

$Features = @{
    "M" = "main"
    "1" = "f1"
    "2" = "f2"
    "3" = "f3"
    "4" = "f4"
}

# ---------- Helpers ----------
function Get-WorktreePath($name) {
    Join-Path $WorktreeRoot $name
}

function Test-WorktreeExists($name) {
    Test-Path (Get-WorktreePath $name)
}

function Require-Worktree($name) {
    if (-not (Test-WorktreeExists $name)) {
        Write-Host "Worktree '$name' does not exist." -ForegroundColor Red
        Read-Host "Press ENTER to continue"
        return $false
    }
    return $true
}

function Invoke-Git {
    param (
        [string]$Path,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$GitArgs
    )
    & git -C $Path @GitArgs
}

function Get-GitDirty($path) {
    $out = Invoke-Git $path status --porcelain
    return -not [string]::IsNullOrWhiteSpace($out)
}

# ---------- Menus ----------
function Show-FeatureMenu {
    Clear-Host
    Write-Host "Select FEATURE:`n"
    Write-Host "  Key  Feature  Exists"
    Write-Host "  ---  -------  ------"

    foreach ($key in $FeatureOrder) {
        $name   = $Features[$key]
        $exists = if (Test-WorktreeExists $name) { "Yes" } else { "No" }
        Write-Host ("   {0,-2}  {1,-7} {2}" -f $key, $name, $exists)
    }

    Write-Host ""
    Write-Host "   L   List"
    Write-Host "   Q   Quit`n"
}

function Show-ActionMenu($name) {
    $exists = Test-WorktreeExists $name
    $dirty  = if ($exists) { Get-GitDirty (Get-WorktreePath $name) } else { $false }

    Clear-Host
    Write-Host "Feature: $name   Exists: $(if ($exists) { 'Yes' } else { 'No' })`n"
    Write-Host "Select ACTION:"
    Write-Host "  S  Start"

    if ($exists -and $dirty) {
        Write-Host "  F  Finish"
    }

    if ($exists) {
        Write-Host "  D  Destroy"
    }

    Write-Host "  B  Back"
    Write-Host "  Q  Quit`n"
}

# ---------- Actions ----------
function Start-Feature($name) {
    if (-not (Test-WorktreeExists $name)) {
        Write-Host "Creating worktree '$name'..."
        Push-Location $WorktreeRoot
        git worktree add $name
        Pop-Location
    }

    Write-Host "Started feature '$name'."
    Read-Host "Press ENTER to continue"
}

function Finish-Feature($name) {
    if (-not (Require-Worktree $name)) { return }

    $path = Get-WorktreePath $name

    if (-not (Get-GitDirty $path)) {
        Write-Host "No changes to commit."
        Read-Host "Press ENTER to continue"
        return
    }

    Clear-Host
    Invoke-Git $path status
    Write-Host ""
    Invoke-Git $path diff --stat

    while ($true) {
        Write-Host ""
        Write-Host "V  View full diff"
        Write-Host "C  Commit"
        Write-Host "B  Back"
        $choice = (Read-Host ">").Trim().ToUpper()

        if ($choice -eq "V") {
            Invoke-Git $path diff --color=always | more
            continue
        }

        if ($choice -eq "B") {
            return
        }

        if ($choice -eq "C") {
            break
        }
    }

    do {
        $msg = Read-Host "Commit message"
    } while ([string]::IsNullOrWhiteSpace($msg))

    Invoke-Git $path add -A
    Invoke-Git $path commit -m $msg

    Write-Host "`nCreated commit:"
    Invoke-Git $path log -1 --oneline

    Read-Host "`nPress ENTER to continue"
}

function Destroy-Feature($name) {
    if (-not (Require-Worktree $name)) { return }

    $confirm = Read-Host "Type YES to destroy worktree '$name'"
    if ($confirm -ne "YES") { return }

    Push-Location $WorktreeRoot
    git worktree remove $name
    Pop-Location

    Write-Host "Destroyed '$name'."
    Read-Host "Press ENTER to continue"
}

function List-Worktrees {
    Clear-Host
    Write-Host "Worktrees:`n"
    foreach ($key in $FeatureOrder) {
        $name   = $Features[$key]
        $exists = if (Test-WorktreeExists $name) { "Yes" } else { "No" }
        Write-Host ("  {0,-2} {1,-7} Exists: {2}" -f $key, $name, $exists)
    }
    Read-Host "`nPress ENTER to return"
}

# ---------- Main Loop ----------
while ($true) {
    Show-FeatureMenu
    $key = (Read-Host ">").Trim().ToUpper()

    if ($key -eq "Q") { break }
    if ($key -eq "L") { List-Worktrees; continue }
    if (-not $Features.ContainsKey($key)) { continue }

    $name = $Features[$key]

    while ($true) {
        Show-ActionMenu $name
        $action = (Read-Host ">").Trim().ToUpper()

        switch ($action) {
            "S" { Start-Feature  $name; break }
            "F" { Finish-Feature $name; break }
            "D" { Destroy-Feature $name; break }
            "B" { break }
            "Q" { exit }
        }
    }
}
