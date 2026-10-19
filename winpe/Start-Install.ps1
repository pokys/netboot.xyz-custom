#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
try {
    # Never launch a deployment from the technician's normal Windows session.
    if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT')) {
        throw 'This launcher may only run inside Windows PE.'
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Import-Module PackageManagement -RequiredVersion '1.4.8.1' -ErrorAction Stop
    Import-Module PowerShellGet -RequiredVersion '2.2.5' -ErrorAction Stop
    Import-PackageProvider -Name NuGet -MinimumVersion '2.8.5.201' -ErrorAction Stop | Out-Null
    if (-not (Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue)) {
        Register-PSRepository -Default -ErrorAction Stop
    }
    Import-Module OSD -RequiredVersion '26.10.6.1' -ErrorAction Stop
    Import-Module "$env:SystemRoot\System32\OSDCloud.Runtime.psm1" -Force -ErrorAction Stop
    Write-Host 'Checking OSDCloud requirements before deployment...' -ForegroundColor Cyan
    Test-OSDCloudRequirements | Out-Null
    Get-Command Start-OSDCloudGUI -ErrorAction Stop | Out-Null
    $disks = @(Get-Disk | Where-Object { $_.BusType -notin @('USB', 'SD') })
    if ($disks.Count -eq 0) { throw 'No installation disk found. Load the storage driver and try again.' }
    Write-Host 'Windows 10 / 11 installation via OSDCloud' -ForegroundColor Cyan
    $disks | Select-Object Number, FriendlyName, BusType, @{Name='SizeGB'; Expression={[math]::Round($_.Size / 1GB)}} | Format-Table -AutoSize
    Write-Warning 'OSDCloud can erase a disk. Verify the target in its installation prompts.'
    Write-Host 'Choose Windows 10 22H2 or a Windows 11 release, edition, and language (cs-cz for Czech) in the next window.'
    if ((Read-Host 'Type INSTALL to open OSDCloud, or press Enter to cancel') -cne 'INSTALL') {
        Write-Host 'Cancelled. No deployment was started.'
        exit 0
    }
    # Interactive GUI only; never pass ZTI or start an unattended deployment here.
    Start-OSDCloudGUI
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    exit 1
}
