#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$errorsFound = @()
Get-ChildItem -LiteralPath $root -Recurse -File |
    Where-Object { $_.Extension -in @('.ps1', '.psm1') -and $_.FullName -notmatch '[\\/](\.git|\.build|artifacts)[\\/]' } |
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
    param([bool]$InWinPE, [bool]$HasDisk, [bool]$ExpectGUI, [int]$ExpectedExit)
    $state = @{ GuiCalled = $false }
    function Test-Path { param($Path) return $InWinPE }
    function Import-Module { param($Name, $RequiredVersion, $ErrorAction, [switch]$Force) }
    function Test-OSDCloudRequirements { return @{Passed=$true} }
    function Import-PackageProvider { param($Name, $MinimumVersion, $ErrorAction) }
    function Get-PSRepository { param($Name, $ErrorAction) return @{Name='PSGallery'} }
    function Get-Command { param($Name, $ErrorAction) return $Name }
    function Get-Disk {
        if ($HasDisk) { [pscustomobject]@{Number=0; FriendlyName='TEST ONLY'; BusType='NVMe'; Size=64GB} }
    }
    function Read-Host { throw 'Launcher must open the GUI without a text confirmation.' }
    function Start-OSDCloudGUI { $state.GuiCalled = $true }
    $global:LASTEXITCODE = 0
    & (Join-Path $root 'winpe\Start-Install.ps1') | Out-Null
    if ($state.GuiCalled -ne $ExpectGUI -or $LASTEXITCODE -ne $ExpectedExit) {
        throw "Launcher check failed: WinPE=$InWinPE HasDisk=$HasDisk"
    }
}
Test-Launcher -InWinPE $false -HasDisk $true -ExpectGUI $false -ExpectedExit 1
Test-Launcher -InWinPE $true -HasDisk $false -ExpectGUI $false -ExpectedExit 1
Test-Launcher -InWinPE $true -HasDisk $true -ExpectGUI $true -ExpectedExit 0
$defaults = Get-Content -LiteralPath (Join-Path $root 'winpe\Start-OSDCloudGUI.json') -Raw | ConvertFrom-Json
if ((@($defaults.PSObject.Properties.Name | Sort-Object) -join ',') -ne 'OSActivation,OSEdition,OSLanguage' -or
    $defaults.OSEdition -ne 'Pro' -or $defaults.OSLanguage -ne 'cs-cz' -or $defaults.OSActivation -ne 'Retail') {
    throw 'GUI defaults must only preselect Pro, cs-cz and Retail; leave OS and hardware detection to OSDCloud.'
}
Write-Host 'PASS: PowerShell syntax, iPXE targets, desktop refusal, missing disk, direct interactive GUI, scoped defaults.'
