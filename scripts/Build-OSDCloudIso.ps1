#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$AssetsPath = (Join-Path $PSScriptRoot '..\artifacts\osdcloud'),
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\artifacts\osdcloud-iso'),
    [string]$WorkPath = (Join-Path $PSScriptRoot '..\.build\osdcloud-iso'),
    [string]$AdkRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit"
)
$ErrorActionPreference = 'Stop'
$AssetsPath = [IO.Path]::GetFullPath($AssetsPath)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$WorkPath = [IO.Path]::GetFullPath($WorkPath)
if ((Test-Path -LiteralPath $WorkPath) -or (Test-Path -LiteralPath $OutputPath)) {
    throw 'ISO work/output directories must be new.'
}
$wim = Join-Path $AssetsPath 'boot.wim'
$hashLine = @(Get-Content -LiteralPath (Join-Path $AssetsPath 'SHA256SUMS') |
    Where-Object { $_ -match '^[a-fA-F0-9]{64}\s+boot\.wim$' })
if ($hashLine.Count -ne 1) { throw 'Missing or ambiguous boot.wim checksum.' }
$wimHash = (Get-FileHash -LiteralPath $wim -Algorithm SHA256).Hash.ToLowerInvariant()
if ($wimHash -ne ($hashLine[0] -split '\s+')[0]) { throw 'Source boot.wim checksum mismatch.' }
$peRoot = Join-Path $AdkRoot 'Windows Preinstallation Environment\amd64'
$oscdimgRoot = Join-Path $AdkRoot 'Deployment Tools\amd64\Oscdimg'
$oscdimg = Join-Path $oscdimgRoot 'oscdimg.exe'
function Find-BootSector([string]$Name) {
    foreach ($folder in @((Join-Path $peRoot 'fwfiles'), $oscdimgRoot)) {
        $candidate = Join-Path $folder $Name
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw "Missing ADK boot sector: $Name"
}
$bios = Find-BootSector 'etfsboot.com'
$efi = Find-BootSector 'efisys.bin'
if (-not (Test-Path -LiteralPath $oscdimg -PathType Leaf)) { throw 'Missing ADK oscdimg.exe.' }
$media = New-Item -ItemType Directory -Path (Join-Path $WorkPath 'media') -Force
Copy-Item -Path (Join-Path $peRoot 'Media\*') -Destination $media.FullName -Recurse -Force
$sources = New-Item -ItemType Directory -Path (Join-Path $media.FullName 'sources') -Force
Copy-Item -LiteralPath $wim -Destination (Join-Path $sources.FullName 'boot.wim')
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
$iso = Join-Path $OutputPath 'osdcloud-v4-direct.iso'
# One El Torito entry for BIOS and another for x64 UEFI; no iPXE/wimboot.
Copy-Item -LiteralPath $bios -Destination (Join-Path $WorkPath 'etfsboot.com')
Copy-Item -LiteralPath $efi -Destination (Join-Path $WorkPath 'efisys.bin')
Push-Location -LiteralPath $WorkPath
try {
    & $oscdimg '-m' '-o' '-u2' '-udfver102' '-bootdata:2#p0,e,betfsboot.com#pEF,e,befisys.bin' $media.FullName $iso
    if ($LASTEXITCODE -ne 0) { throw "ISO creation failed: $LASTEXITCODE" }
}
finally { Pop-Location }
$isoHash = (Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash.ToLowerInvariant()
"$isoHash  osdcloud-v4-direct.iso" | Set-Content -LiteralPath (Join-Path $OutputPath 'SHA256SUMS') -Encoding Ascii
"$wimHash  boot.wim (unchanged from osdcloud-v4)" |
    Set-Content -LiteralPath (Join-Path $OutputPath 'SOURCE-WIM-SHA256.txt') -Encoding Ascii
Write-Host "Direct BIOS/UEFI boot ISO ready: $iso"
