# scripts\test_headless.ps1
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$Env:PYTHONPATH = "$RepoRoot\src"
Push-Location $RepoRoot
try {
  pytest -q
} finally {
  Pop-Location
}
