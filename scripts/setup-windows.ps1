# EventLyra: entorno en E:\ para la PC con RTX 4070 SUPER.
# No guarda tokens en el repositorio. El login de Hugging Face es interactivo.
# No bajes TranslateGemma 12B ni 27B: este corte usa solo el 4B.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$TorchIndex = "https://download.pytorch.org/whl/cu128"
$ModeloGemma = "google/translategemma-4b-it"
$ModeloWhisper = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Assert-FueraDeC {
    param(
        [Parameter(Mandatory = $true)][string]$Ruta,
        [Parameter(Mandatory = $true)][string]$Nombre
    )
    $full = [System.IO.Path]::GetFullPath($Ruta)
    if ($full -match '^[Cc]:\\') {
        throw "$Nombre no puede quedar en C:\ ($full). Usá E:\ u otro disco con espacio."
    }
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Find-PythonLauncher {
    Refresh-Path
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("-3.12", "-3.11", "-3")) {
            & py $ver -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
            if ($LASTEXITCODE -eq 0) {
                return ,@("py", $ver)
            }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return ,@("python")
        }
    }
    return $null
}

if ($ModeloGemma -ne "google/translategemma-4b-it") {
    throw "Este corte solo baja google/translategemma-4b-it."
}

$Raiz = "E:\EventLyra"
$Venv = Join-Path $Raiz "venv"
$HfHome = Join-Path $Raiz "hf-home"
$Work = Join-Path $Raiz "work"
$Hub = Join-Path $HfHome "hub"

Assert-FueraDeC -Ruta $Venv -Nombre "El entorno virtual"
Assert-FueraDeC -Ruta $HfHome -Nombre "HF_HOME"
Assert-FueraDeC -Ruta $Work -Nombre "El directorio de trabajo"

Write-Host "Repositorio: $Repo"
Write-Host "Entorno virtual: $Venv"
Write-Host "HF_HOME: $HfHome"
Write-Host "Trabajo: $Work"

New-Item -ItemType Directory -Force -Path $Raiz, $HfHome, $Hub, $Work | Out-Null

$launcher = Find-PythonLauncher
if (-not $launcher) {
    Write-Host "No hay Python 3.11+. Se intenta instalar Python 3.12 con winget (el intérprete puede quedar en el perfil; el venv va a E:\)."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Instalá Python 3.11 o 3.12 desde https://www.python.org/downloads/ y volvé a correr este script."
    }
    winget install --id Python.Python.3.12 -e --scope user --accept-package-agreements --accept-source-agreements
    $launcher = Find-PythonLauncher
    if (-not $launcher) {
        throw "Python se instaló pero esta consola no lo ve. Abrí una terminal nueva y volvé a correr el script."
    }
}

if (Test-Path $Venv) {
    Write-Host "El venv ya existe en $Venv. Se reutiliza."
} else {
    if ($launcher.Length -eq 1) {
        & $launcher[0] -m venv $Venv
    } else {
        & $launcher[0] $launcher[1] -m venv $Venv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo crear el venv en $Venv."
    }
}

$Python = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "No se encontró $Python."
}

& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip no pudo actualizarse." }

Write-Host "Se instalan las dependencias de la aplicación."
& $Python -m pip install -r (Join-Path $Repo "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }

Write-Host "Se instala torch desde $TorchIndex para que CUDA quede por encima de la rueda de CPU."
& $Python -m pip install --force-reinstall torch --index-url $TorchIndex
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar torch con CUDA. Revisá el driver de la RTX 4070 SUPER y $TorchIndex." }

Write-Host "Se reinstala bitsandbytes sin tocar torch."
& $Python -m pip install --force-reinstall --no-deps bitsandbytes
if ($LASTEXITCODE -ne 0) { throw "No se pudo reinstalar bitsandbytes." }

& $Python -c "import torch; print(torch.__version__); raise SystemExit(0 if torch.cuda.is_available() else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "torch.cuda.is_available() dio False. Actualizá el driver NVIDIA y volvé a correr el script. Sin CUDA este corte no transcribe."
}

& $Python -c "import faster_whisper, transformers, fastapi, bitsandbytes; print('dependencias listas')"
if ($LASTEXITCODE -ne 0) { throw "Falta alguna dependencia de Python." }

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "Se instala ffmpeg."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "No está ffmpeg ni winget. Instalá ffmpeg y dejalo en el PATH: https://www.gyan.dev/ffmpeg/builds/"
    }
    winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
    Refresh-Path
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        throw "ffmpeg se instaló pero esta consola no lo ve. Abrí una terminal nueva, comprobá 'ffmpeg -version' y volvé a correr el script."
    }
}

[Environment]::SetEnvironmentVariable("HF_HOME", $HfHome, "User")
[Environment]::SetEnvironmentVariable("HUGGINGFACE_HUB_CACHE", $Hub, "User")
$env:HF_HOME = $HfHome
$env:HUGGINGFACE_HUB_CACHE = $Hub

$Hf = Join-Path $Venv "Scripts\huggingface-cli.exe"
if (-not (Test-Path $Hf)) {
    throw "No se encontró huggingface-cli en el venv."
}

Write-Host ""
Write-Host "Credenciales, antes de bajar pesos:"
Write-Host "  1. Creá una cuenta en https://huggingface.co/join si todavía no tenés."
Write-Host "  2. Aceptá la licencia Gemma en https://huggingface.co/$ModeloGemma"
Write-Host "  3. Creá un token de lectura en https://huggingface.co/settings/tokens"
Write-Host "El token lo guarda el CLI de Hugging Face. No lo pongas en el repositorio ni en un .env versionado."
Write-Host "Los pesos van a $HfHome (no a C:\ y no al git)."
Read-Host "Cuando la licencia del 4B esté aceptada, apretá Enter para hacer huggingface-cli login"

& $Hf login
if ($LASTEXITCODE -ne 0) { throw "huggingface-cli login no terminó bien." }

Write-Host "Se baja solo $ModeloGemma"
& $Hf download $ModeloGemma
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo bajar $ModeloGemma. Confirmá el login y que la licencia figura aceptada en la página del modelo."
}

Write-Host "Se baja faster-whisper turbo ($ModeloWhisper) para ejecutarlo en INT8."
& $Hf download $ModeloWhisper
if ($LASTEXITCODE -ne 0) { throw "No se pudo bajar $ModeloWhisper." }

Write-Host ""
Write-Host "Setup listo."
Write-Host "Para dos sesiones en esta GPU:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\run-windows.ps1`" -SessionsPerGpu 2"
Write-Host "K es ese parámetro. Para más sesiones en la misma GPU, subilo. Para otra GPU u otra máquina, corré el mismo API con su propio K."
