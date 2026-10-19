#Requires -Version 5.1
#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\artifacts\osdcloud'),
    [string]$WorkPath = (Join-Path $PSScriptRoot '..\.build\osdcloud'),
    [string]$AdkRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit",
    [string]$DriverPath
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSEdition -ne 'Desktop' -or -not [Environment]::Is64BitProcess) {
    throw 'Run this script in elevated 64-bit Windows PowerShell 5.1 (powershell.exe).'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$peRoot = Join-Path $AdkRoot 'Windows Preinstallation Environment\amd64'
$sourceWim = Join-Path $peRoot 'en-us\winpe.wim'
$ocRoot = Join-Path $peRoot 'WinPE_OCs'
$dism = Join-Path $AdkRoot 'Deployment Tools\amd64\DISM\dism.exe'
# Dependency order is required by Microsoft WinPE optional components.
$packages = @('WinPE-WMI', 'WinPE-NetFX', 'WinPE-Scripting', 'WinPE-PowerShell', 'WinPE-StorageWMI', 'WinPE-DismCmdlets', 'WinPE-HTA', 'WinPE-SecureStartup')
$bootFiles = @{ 'BCD' = (Join-Path $peRoot 'Media\Boot\BCD'); 'boot.sdi' = (Join-Path $peRoot 'Media\Boot\boot.sdi') }
foreach ($required in @($sourceWim, $dism) + @($bootFiles.Values) + @($packages | ForEach-Object { Join-Path $ocRoot "$_.cab" })) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing ADK/WinPE component: $required. Install Deployment Tools and the matching WinPE add-on."
    }
}
if ($DriverPath -and -not (Test-Path -LiteralPath $DriverPath -PathType Container)) {
    throw 'DriverPath must be an existing directory containing extracted, signed x64 INF drivers.'
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$WorkPath = [IO.Path]::GetFullPath($WorkPath)
# A fresh work directory avoids reusing an image left mounted by a failed build.
if (Test-Path -LiteralPath $WorkPath) { throw "WorkPath already exists. Use a new directory: $WorkPath" }
if (Test-Path -LiteralPath (Join-Path $OutputPath 'boot.wim')) { throw 'Output boot.wim already exists. Choose a new OutputPath.' }
New-Item -ItemType Directory -Path $WorkPath -Force | Out-Null
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
$mount = New-Item -ItemType Directory -Path (Join-Path $WorkPath 'mount')
$image = Join-Path $WorkPath 'boot.wim'
Copy-Item -LiteralPath $sourceWim -Destination $image

function Invoke-AdkDism {
    param([string[]]$DismArguments)
    & $dism @DismArguments
    if ($LASTEXITCODE -notin @(0, 3010)) { throw "DISM failed with exit code $LASTEXITCODE" }
}

$mounted = $false
try {
    Invoke-AdkDism -DismArguments @('/Mount-Image', "/ImageFile:$image", '/Index:1', "/MountDir:$($mount.FullName)")
    $mounted = $true
    foreach ($package in $packages) {
        Invoke-AdkDism -DismArguments @("/Image:$($mount.FullName)", '/Add-Package', "/PackagePath:$ocRoot\$package.cab")
        $languageCab = Join-Path $ocRoot "en-us\${package}_en-us.cab"
        if (Test-Path -LiteralPath $languageCab) {
            Invoke-AdkDism -DismArguments @("/Image:$($mount.FullName)", '/Add-Package', "/PackagePath:$languageCab")
        }
    }
    Invoke-AdkDism -DismArguments @("/Image:$($mount.FullName)", '/Set-ScratchSpace:512')
    if ($DriverPath) {
        Invoke-AdkDism -DismArguments @("/Image:$($mount.FullName)", '/Add-Driver', "/Driver:$([IO.Path]::GetFullPath($DriverPath))", '/Recurse')
    }
    # Pin the PowerShell 5.1-compatible OSD implementation used by this launcher.
    # This is the standalone OSD module, not the newer OSDeploy build tooling.
    $modules = Join-Path $mount.FullName 'Program Files\WindowsPowerShell\Modules'
    New-Item -ItemType Directory -Path $modules -Force | Out-Null
    Save-Module -Name OSD -RequiredVersion '26.10.6.1' -Repository PSGallery -Path $modules -Force
    # WinPE's optional PowerShell component alone cannot load PowerShellGet.
    # Include its complete PS 5.1 dependencies and an offline NuGet provider.
    Save-Module -Name PackageManagement -RequiredVersion '1.4.8.1' -Repository PSGallery -Path $modules -Force
    Save-Module -Name PowerShellGet -RequiredVersion '2.2.5' -Repository PSGallery -Path $modules -Force
    $provider = Get-PackageProvider -Name NuGet -ListAvailable |
        Where-Object { $_.Version -ge [version]'2.8.5.201' } | Sort-Object Version -Descending | Select-Object -First 1
    if (-not $provider -or -not (Test-Path -LiteralPath $provider.ProviderPath -PathType Leaf)) {
        throw 'An installed NuGet provider is required on the build runner.'
    }
    $providerFolder = Join-Path $mount.FullName "Program Files\PackageManagement\ProviderAssemblies\nuget\$($provider.Version)"
    New-Item -ItemType Directory -Path $providerFolder -Force | Out-Null
    Copy-Item -LiteralPath $provider.ProviderPath -Destination $providerFolder
    if ($DriverPath -and (Test-Path -LiteralPath (Join-Path $DriverPath 'winpe-virtual-drivers.json'))) {
        Copy-Item -LiteralPath (Join-Path $DriverPath 'winpe-virtual-drivers.json') -Destination (Join-Path $OutputPath 'virtual-drivers.json')
    }
    # Preserve the injected provider/version evidence in the release artifacts.
    Invoke-AdkDism -DismArguments @("/Image:$($mount.FullName)", '/Get-Drivers', '/Format:Table')
    $system32 = Join-Path $mount.FullName 'Windows\System32'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\winpe\Start-Install.ps1') -Destination $system32
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\winpe\startnet.cmd') -Destination $system32
    Invoke-AdkDism -DismArguments @('/Unmount-Image', "/MountDir:$($mount.FullName)", '/Commit')
    $mounted = $false

    $wimboot = Join-Path $WorkPath 'wimboot'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/ipxe/wimboot/releases/download/v2.9.0/wimboot' -OutFile $wimboot
    $expected = '5f067ccdc4d084d5bf77b6c853bd0f8402dfc2b4cd1b103d358993ae97fae8e3'
    if ((Get-FileHash -LiteralPath $wimboot -Algorithm SHA256).Hash -ne $expected) { throw 'wimboot SHA256 mismatch.' }
    Copy-Item -LiteralPath $wimboot -Destination $OutputPath
    # The base ADK WIM is not complete installation media: its BCD and SDI
    # are separate files. Supply both explicitly to wimboot.
    foreach ($name in $bootFiles.Keys) {
        Copy-Item -LiteralPath $bootFiles[$name] -Destination (Join-Path $OutputPath $name)
    }
    # Publish the WIM last, so incomplete builds do not look ready to boot.
    Copy-Item -LiteralPath $image -Destination $OutputPath
    Get-ChildItem -LiteralPath $OutputPath -File | Where-Object Name -in @('boot.wim', 'wimboot', 'BCD', 'boot.sdi') |
        Get-FileHash -Algorithm SHA256 | ForEach-Object { '{0}  {1}' -f $_.Hash.ToLowerInvariant(), [IO.Path]::GetFileName($_.Path) } |
        Set-Content -LiteralPath (Join-Path $OutputPath 'SHA256SUMS') -Encoding Ascii
    Write-Host "Boot assets ready: $OutputPath"
}
finally {
    if ($mounted) {
        Invoke-AdkDism -DismArguments @('/Unmount-Image', "/MountDir:$($mount.FullName)", '/Discard')
    }
}
