param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonLauncher = "py"
    $PythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonLauncher = "python"
    $PythonArgs = @()
} else {
    throw "未找到 Python 3，请先安装 Python 3.10+。"
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $PythonLauncher @PythonArgs -m venv .venv
}

if ($CliArgs.Count -eq 0) {
    & $VenvPython main.py --interactive
} else {
    & $VenvPython main.py @CliArgs
}
exit $LASTEXITCODE
