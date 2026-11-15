[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$CompilerCandidates = @(
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$Compiler = $CompilerCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Compiler) {
    throw "The Windows .NET Framework C# compiler was not found. Use Launch_ASTRA.cmd instead."
}

$Source = Join-Path $Root "packaging\windows\AstraLauncher.cs"
$Output = Join-Path $Root "Launch_ASTRA.exe"
& $Compiler /nologo /optimize+ /target:exe "/out:$Output" $Source
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Output)) { throw "Launcher compilation failed." }
Write-Host "Created $Output"
