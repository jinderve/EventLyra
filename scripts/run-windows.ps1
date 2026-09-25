# EventLyra: levanta un proceso. K es obligatorio y no tiene valor por defecto.
param(
    [Parameter(Mandatory = $true)]
    [int]$SessionsPerGpu,
    [string]$Venv = "E:\EventLyra\venv",
    [string]$HfHome = "E:\EventLyra\hf-home",
    [string]$WorkDir = "E:\EventLyra\work",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

function Assert-FueraDeC {
    param(
        [Parameter(Mandatory = $true)][string]$Ruta,
        [Parameter(Mandatory = $true)][string]$Nombre
    )
    $full = [System.IO.Path]::GetFullPath($Ruta)
    if ($full -match '^[Cc]:\\') {
        throw "$Nombre no puede quedar en C:\ ($full)."
    }
}

if ($SessionsPerGpu -lt 1) {
    throw "-SessionsPerGpu (K) tiene que ser un entero mayor o igual que 1."
}

Assert-FueraDeC -Ruta $Venv -Nombre "El entorno virtual"
Assert-FueraDeC -Ruta $HfHome -Nombre "HF_HOME"
Assert-FueraDeC -Ruta $WorkDir -Nombre "El directorio de trabajo"

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "No se encontró $Python. Corré primero scripts\setup-windows.ps1 en la PC con la GPU."
}

New-Item -ItemType Directory -Force -Path $WorkDir, $HfHome | Out-Null
$env:HF_HOME = $HfHome
$env:HUGGINGFACE_HUB_CACHE = Join-Path $HfHome "hub"

Set-Location $Repo
Write-Host "K = $SessionsPerGpu. Una sola copia de los modelos atiende esas sesiones."
Write-Host "Abrí http://127.0.0.1:$Port"
& $Python -m eventlyra --sessions-per-gpu $SessionsPerGpu --work-dir $WorkDir --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
