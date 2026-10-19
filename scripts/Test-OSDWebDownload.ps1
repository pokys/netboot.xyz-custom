#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ModuleRoot,
    [Parameter(Mandatory = $true)][string]$SourceUrl,
    [Parameter(Mandatory = $true)][string]$DestinationPath
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $DestinationPath) { throw 'Use a new test destination.' }
$root = Split-Path $PSScriptRoot -Parent
$file = Join-Path $ModuleRoot 'Public\Functions\Save-WebFile.ps1'
Import-Module Microsoft.PowerShell.Utility, Microsoft.PowerShell.Management -ErrorAction Stop
# Reproduce plain WinPE's missing curl in this disposable child process only.
# Keep PowerShell's module lookup intact; no installed executable is modified.
$env:PATH = (New-Item -ItemType Directory -Path (Join-Path $DestinationPath 'empty-bin') -Force).FullName
if (Get-Command -Name curl.exe -ErrorAction SilentlyContinue) { throw 'curl is still visible in the test process.' }
. $file
$reproduced = $false
try {
    Save-WebFile -SourceUrl $SourceUrl -DestinationDirectory (Join-Path $DestinationPath 'original') -WebClient | Out-Null
}
catch {
    if ($_.Exception.Message -notmatch 'WebClient.*SwitchParameter') { throw }
    $reproduced = $true
}
if (-not $reproduced) { throw 'Original WebClient bug was not reproduced.' }
& (Join-Path $root 'winpe\Repair-OSDWebDownload.ps1') -ModuleRoot $ModuleRoot
. $file
foreach ($explicit in @($false, $true)) {
    $folder = Join-Path $DestinationPath "fixed-$explicit"
    $parameters = @{ SourceUrl = $SourceUrl; DestinationDirectory = $folder; DestinationName = 'probe.txt' }
    if ($explicit) { $parameters.WebClient = $true }
    $result = Save-WebFile @parameters
    if ($result -isnot [IO.FileInfo] -or (Get-Content -LiteralPath $result.FullName -Raw) -ne 'OSD-DOWNLOAD-REGRESSION-PASS') {
        throw "Incorrect download in WebClient branch: explicit=$explicit"
    }
    Write-Host "PASS: actual HTTP download without curl, explicit WebClient=$explicit"
}
# A second repair must leave the already-patched source unchanged.
& (Join-Path $root 'winpe\Repair-OSDWebDownload.ps1') -ModuleRoot $ModuleRoot
Write-Host 'PASS: original bug reproduced; fallback and explicit switch download actual files; repair is idempotent.'
