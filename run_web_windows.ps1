$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" -m paper_lab.web --offline @args
} else {
    & py -3 -m paper_lab.web --offline @args
}
