#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$errorsFound = @()
Get-ChildItem -LiteralPath $root -Recurse -Filter '*.ps1' |
    Where-Object { $_.FullName -notmatch '[\\/](\.git|\.build|artifacts)[\\/]' } |
    ForEach-Object {
        $parseErrors = $null
        [Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$parseErrors) | Out-Null
        $errorsFound += @($parseErrors)
    }
if ($errorsFound.Count) { throw ($errorsFound | Out-String) }
foreach ($file in @('custom.ipxe', 'windows.ipxe', 'esxi.ipxe')) {
    $lines = Get-Content -LiteralPath (Join-Path $root $file)
    if ($lines[0] -ne '#!ipxe') { throw "Missing iPXE header: $file" }
    $labels = @($lines | Where-Object { $_ -match '^:[\w-]+$' } | ForEach-Object { $_.Substring(1) })
    if (@($labels | Group-Object | Where-Object Count -gt 1).Count) { throw "Duplicate labels: $file" }
    foreach ($line in $lines) {
        foreach ($match in [regex]::Matches($line, '\bgoto ([a-zA-Z_][\w-]*)')) {
            if ($match.Groups[1].Value -notin $labels) { throw "Missing goto target in ${file}: $line" }
        }
        if ($line -match '^item\s+(?!-)([\w-]+)\s' -and $Matches[1] -notin $labels) {
            throw "Missing menu target in ${file}: $line"
        }
    }
}
# Mock every external action: never start an actual deployment during tests.
function Test-Launcher {
    param([bool]$InWinPE, [string]$Answer, [bool]$HasDisk, [bool]$ExpectGUI, [int]$ExpectedExit)
    $state = @{ GuiCalled = $false }
    function Test-Path { param($Path) return $InWinPE }
    function Import-Module { param($Name, $RequiredVersion, $ErrorAction) }
    function Get-Command { param($Name, $ErrorAction) return $Name }
    function Get-Disk {
        if ($HasDisk) { [pscustomobject]@{Number=0; FriendlyName='TEST ONLY'; BusType='NVMe'; Size=64GB} }
    }
    function Read-Host { param($Prompt) return $Answer }
    function Start-OSDCloudGUI { $state.GuiCalled = $true }
    $global:LASTEXITCODE = 0
    & (Join-Path $root 'winpe\Start-Install.ps1') | Out-Null
    if ($state.GuiCalled -ne $ExpectGUI -or $LASTEXITCODE -ne $ExpectedExit) {
        throw "Launcher check failed: WinPE=$InWinPE Answer=$Answer HasDisk=$HasDisk"
    }
}
Test-Launcher -InWinPE $false -Answer INSTALL -HasDisk $true -ExpectGUI $false -ExpectedExit 1
Test-Launcher -InWinPE $true -Answer '' -HasDisk $true -ExpectGUI $false -ExpectedExit 0
Test-Launcher -InWinPE $true -Answer INSTALL -HasDisk $false -ExpectGUI $false -ExpectedExit 1
Test-Launcher -InWinPE $true -Answer INSTALL -HasDisk $true -ExpectGUI $true -ExpectedExit 0
Write-Host 'PASS: PowerShell syntax, iPXE targets, desktop refusal, cancellation, missing disk, interactive launch.'
