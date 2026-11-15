[CmdletBinding()]
param(
    [switch]$SkipOllamaInstall,
    [switch]$SkipModel
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DataRoot = if ($env:ASTRA_DATA_DIR) { $env:ASTRA_DATA_DIR } else { Join-Path ([Environment]::GetFolderPath("UserProfile")) ".astra\data" }
$LogDir = Join-Path $DataRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir ("setup-{0}-{1}.log" -f (Get-Date -Format "yyyyMMdd-HHmmssfff"), $PID)
Start-Transcript -Path $LogPath | Out-Null

function Require-Command([string]$Name, [string]$Help) {
    $Command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $Command) { throw "$Name is required. $Help" }
    return $Command.Source
}

try {
    Write-Host "ASTRA setup started in $Root"
    $Python = Require-Command "python" "Install Python 3.10-3.13 from https://www.python.org/downloads/."
    $VersionOk = & $Python -c "import sys; print(int((3,10) <= sys.version_info[:2] < (3,14)))"
    if ($VersionOk -ne "1") { throw "ASTRA requires Python 3.10-3.13." }

    $Node = Require-Command "node" "Install Node.js 22 or 24 LTS from https://nodejs.org/."
    $Npm = Require-Command "npm.cmd" "Install npm with Node.js."
    $NodeMajor = [int]((& $Node --version).TrimStart("v").Split(".")[0])
    if ($NodeMajor -lt 22) { throw "ASTRA requires Node.js 22 or newer." }

    $Venv = Join-Path $Root ".venv"
    if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
        & $Python -m venv $Venv
    }
    $VenvPython = Join-Path $Venv "Scripts\python.exe"
    & $VenvPython -m pip install --disable-pip-version-check --requirement (Join-Path $Root "backend\requirements.lock") --editable (Join-Path $Root "backend")

    Push-Location (Join-Path $Root "frontend")
    try { & $Npm ci } finally { Pop-Location }

    & $VenvPython (Join-Path $Root "scripts\initialize.py")

    $OllamaCommand = Get-Command "ollama.exe" -ErrorAction SilentlyContinue
    $OllamaPath = if ($OllamaCommand) { $OllamaCommand.Source } else { $null }
    if (-not $OllamaPath -and -not $SkipOllamaInstall) {
        $Winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
        if ($Winget) {
            Write-Host "Installing Ollama from the verified Windows Package Manager source..."
            & $Winget.Source install --id Ollama.Ollama --exact --accept-package-agreements --accept-source-agreements
            $KnownOllama = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Programs\Ollama\ollama.exe"
            if (Test-Path $KnownOllama) { $OllamaPath = $KnownOllama }
        } else {
            Write-Warning "Ollama was not installed because Windows Package Manager is unavailable. ASTRA will use offline mode."
        }
    }

    if ($OllamaPath -and -not $SkipModel) {
        $Model = if ($env:ASTRA_OLLAMA_MODEL) { $env:ASTRA_OLLAMA_MODEL } else { "qwen3:8b" }
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
        } catch {
            Start-Process -FilePath $OllamaPath -ArgumentList "serve" -WindowStyle Hidden | Out-Null
            $Deadline = (Get-Date).AddSeconds(20)
            while ((Get-Date) -lt $Deadline) {
                try {
                    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
                    break
                } catch { Start-Sleep -Milliseconds 500 }
            }
        }
        Write-Host "Preparing local model $Model. Existing model layers are reused."
        & $OllamaPath pull $Model
        if ($LASTEXITCODE -ne 0) { throw "Ollama could not prepare model $Model." }
    } elseif (-not $OllamaPath) {
        Write-Warning "Ollama is unavailable. Setup completed with the local AI assistant offline."
    }

    & $VenvPython (Join-Path $Root "scripts\diagnose.py")
    Write-Host "ASTRA setup completed. Launch with .\Launch_ASTRA.cmd"
    Write-Host "Setup log: $LogPath"
} finally {
    Stop-Transcript | Out-Null
}
