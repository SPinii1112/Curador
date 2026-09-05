$ErrorActionPreference = "Stop"
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { $pythonCommand = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCommand) {
    # El proyecto original ya trae un entorno: puede usarse como base para crear
    # uno independiente para Curador, sin instalar nada dentro del original.
    $parentPython = Join-Path (Split-Path -Parent $projectPath) ".venv\Scripts\python.exe"
    if (Test-Path $parentPython) { $pythonCommand = Get-Item $parentPython }
}
if (-not $pythonCommand) { throw "No se encontró Python. Instalá Python 3.10 o superior y volvé a ejecutar este archivo." }
if (-not (Test-Path .venv\Scripts\python.exe)) { & $pythonCommand.Source -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Start-Process "http://127.0.0.1:5000"
& .\.venv\Scripts\python.exe server.py
