[CmdletBinding()]
param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DataRoot = if ($env:ASTRA_DATA_DIR) { $env:ASTRA_DATA_DIR } else { Join-Path ([Environment]::GetFolderPath("UserProfile")) ".astra\data" }
$LogDir = Join-Path $DataRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$Started = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Test-Http([string]$Url) {
    try {
        $Response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $Response.StatusCode -ge 200 -and $Response.StatusCode -lt 400
    } catch { return $false }
}

function Test-Port([int]$Port) {
    $Client = [System.Net.Sockets.TcpClient]::new()
    try { $Client.Connect("127.0.0.1", $Port); return $true } catch { return $false } finally { $Client.Dispose() }
}

function Wait-Http([string]$Url, [int]$Seconds, [string]$Name) {
    $Deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $Deadline) {
        if (Test-Http $Url) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not become ready within $Seconds seconds. Check $LogDir."
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython) -or -not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    Write-Host "ASTRA dependencies are missing. Running setup..."
    & (Join-Path $PSScriptRoot "setup.ps1")
}

$Ollama = Get-Command "ollama.exe" -ErrorAction SilentlyContinue
$Model = if ($env:ASTRA_OLLAMA_MODEL) { $env:ASTRA_OLLAMA_MODEL } else { "qwen3:8b" }
$AiReady = $false
if ($Ollama) {
    if (-not (Test-Http "http://127.0.0.1:11434/api/tags")) {
        $OllamaProcess = Start-Process -FilePath $Ollama.Source -ArgumentList "serve" -WindowStyle Hidden -PassThru
        $Started.Add($OllamaProcess)
        try { Wait-Http "http://127.0.0.1:11434/api/tags" 20 "Ollama" } catch { Write-Warning $_ }
    }
    try {
        $Tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
        $AiReady = @($Tags.models | ForEach-Object { $_.name }) -contains $Model
    } catch { $AiReady = $false }
}
$env:ASTRA_CHAT_MODEL_ENABLED = if ($AiReady) { "1" } else { "0" }
if (-not $AiReady) { Write-Warning "The local AI model is offline. Profiles and forecasts remain available." }

try {
    $HealthUrl = "http://127.0.0.1:8000/api/v1/health"
    if (-not (Test-Http $HealthUrl)) {
        if (Test-Port 8000) { throw "Port 8000 is occupied by another service." }
        $Backend = Start-Process -FilePath $VenvPython -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--no-access-log" -WorkingDirectory (Join-Path $Root "backend") -RedirectStandardOutput (Join-Path $LogDir "backend-$RunId.out.log") -RedirectStandardError (Join-Path $LogDir "backend-$RunId.err.log") -PassThru -WindowStyle Hidden
        $Started.Add($Backend)
    }
    Wait-Http $HealthUrl 60 "ASTRA backend"

    $FrontendUrl = "http://127.0.0.1:5173/"
    if (-not (Test-Http $FrontendUrl)) {
        if (Test-Port 5173) { throw "Port 5173 is occupied by another service." }
        $Npm = (Get-Command "npm.cmd" -ErrorAction Stop).Source
        $Frontend = Start-Process -FilePath $Npm -ArgumentList "run","dev" -WorkingDirectory (Join-Path $Root "frontend") -RedirectStandardOutput (Join-Path $LogDir "frontend-$RunId.out.log") -RedirectStandardError (Join-Path $LogDir "frontend-$RunId.err.log") -PassThru -WindowStyle Hidden
        $Started.Add($Frontend)
    }
    Wait-Http $FrontendUrl 60 "ASTRA frontend"

    if (-not $NoBrowser) { Start-Process $FrontendUrl }
    Write-Host "ASTRA is ready at $FrontendUrl"
    Write-Host "Local AI: $(if ($AiReady) { 'ready' } else { 'offline' })"
    Write-Host "Logs: $LogDir"
    Write-Host "Press Ctrl+C to stop services started by this launcher."
    while ($true) {
        foreach ($Process in $Started) {
            if ($Process.HasExited -and $Process.Id -ne $OllamaProcess.Id) {
                throw "An ASTRA service stopped unexpectedly. Check $LogDir."
            }
        }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($Process in $Started) {
        if (-not $Process.HasExited) {
            & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
        }
    }
}
