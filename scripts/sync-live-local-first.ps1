param(
  [string]$Remote = "origin",
  [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"

function Run-Git {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  & git @Args
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Args -join ' ') failed"
  }
}

$root = (& git rev-parse --show-toplevel).Trim()
Set-Location $root

$status = (& git status --porcelain=v1)
if ($status) {
  Write-Host "Local tree has uncommitted changes. Local-first sync stopped."
  Write-Host "Capture local work first, then rerun:"
  Write-Host "  git add -A"
  Write-Host "  git commit -m `"local-first checkpoint`""
  Write-Host ""
  Write-Host "Current changed files:"
  $status
  exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupBranch = "backup/local-first-$timestamp"

Write-Host "Creating backup branch: $backupBranch"
Run-Git branch $backupBranch

Write-Host "Fetching live branch: $Remote/$Branch"
Run-Git fetch $Remote $Branch

Write-Host "Merging live changes. Conflicts prefer local branch."
Run-Git merge --no-edit -X ours "$Remote/$Branch"

Write-Host "Done. Local kept priority; non-conflicting live changes synced."
