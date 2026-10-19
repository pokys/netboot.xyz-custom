#Requires -Version 5.1
# Test payload served only by the disposable CI VM harness, never installed in PE.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [ValidateSet('windows10','windows11')][string]$OS = 'windows11',
    [ValidateSet('sata','virtio-scsi','vmware')][string]$Devices = 'virtio-scsi'
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
function Send-Report([string]$Name, $Value) {
    $json = $Value | ConvertTo-Json -Depth 10 -Compress
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$Server/evidence/$Name.json" -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($json)) | Out-Null
}
function Send-Logs {
    foreach ($path in @('X:\Windows\Temp\OSDCloud-Requirements.json','X:\ci-deployment.txt','X:\Windows\Logs\DISM\dism.log')) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $name = Split-Path $path -Leaf
            Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$Server/evidence/$name" -ContentType 'text/plain' -InFile $path -ErrorAction SilentlyContinue | Out-Null
        }
    }
    if (Test-Path -LiteralPath 'C:\Windows\TEMP\osdcloud-logs') {
        Get-ChildItem -LiteralPath 'C:\Windows\TEMP\osdcloud-logs' -File | Where-Object {$_.Extension -in @('.log','.txt','.json')} | ForEach-Object {
            Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$Server/evidence/osd-$($_.Name)" -ContentType 'text/plain' -InFile $_.FullName -ErrorAction SilentlyContinue | Out-Null
        }
    }
}
$guardPassed = $false
try {
    if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT')) { throw 'CI deployment requires WinPE.' }
    if ($Server -notmatch '^http://10\.0\.2\.2:[0-9]+$') { throw 'CI result server must be the local QEMU host.' }
    $product = Get-CimInstance Win32_ComputerSystemProduct
    if ($product.Vendor -ne 'QEMU' -or $product.IdentifyingNumber -ne 'OSDCLOUD-CI-ONLY') {
        throw 'This payload refuses to run outside the specifically marked disposable QEMU VM.'
    }
    $disks = @(Get-Disk | Where-Object {$_.BusType -notin @('USB','SD')})
    if ($disks.Count -ne 1 -or $disks[0].SerialNumber.Trim() -ne 'OSDCLOUD-CI-ONLY' -or
        $disks[0].PartitionStyle -ne 'RAW' -or $disks[0].Size -ne 80GB -or $disks[0].Number -ne 0) {
        throw 'Expected one fresh, RAW, 80 GiB disk with the CI-only serial.'
    }
    $guardPassed = $true
    Start-Transcript -LiteralPath 'X:\ci-deployment.txt' -Force | Out-Null
    Import-Module OSD -RequiredVersion '26.10.6.1' -Force
    Send-Report 'storage' @{
        Disks=@(Get-Disk | Select-Object Number,BusType,PartitionStyle,SerialNumber,Size)
        Partitions=@(Get-Partition -ErrorAction SilentlyContinue | Select-Object DiskNumber,PartitionNumber,DriveLetter,AccessPaths)
    }
    $settings = @{
        OSName = $(if ($OS -eq 'windows11') {'Windows 11 25H2 x64'} else {'Windows 10 22H2 x64'})
        OSVersion = $(if ($OS -eq 'windows11') {'Windows 11'} else {'Windows 10'})
        OSReleaseID = $(if ($OS -eq 'windows11') {'25H2'} else {'22H2'})
        OSEdition = 'Pro'
        OSLanguage = 'en-us'
        OSActivation = 'Retail'
        DriverPackName = 'Microsoft Update Catalog'
        ClearDiskConfirm = $true
        restartComputer = $false
        ShutdownSetupComplete = $false
        updateFirmware = $false
        updateDiskDrivers = $true
        updateNetworkDrivers = $true
        updateSCSIDrivers = $true
    }
    $automate = New-Item -ItemType Directory -Path 'X:\OSDCloud\Automate' -Force
    $settings | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $automate.FullName 'Start-OSDCloudGUI.json') -Encoding UTF8
    Send-Report 'ready' @{GuardPassed=$true; DiskSerial='OSDCLOUD-CI-ONLY'; DiskBytes=$disks[0].Size; OS=$OS; Devices=$Devices}
    # The harness operates the actual GUI Start button and answers its disk prompt.
    Start-OSDCloudGUI
    if (-not (Test-Path -LiteralPath 'C:\Windows\System32\ntoskrnl.exe')) { throw 'Deployed Windows kernel is missing.' }
    $drivers = @(Get-WindowsDriver -Path 'C:\' -All -ErrorAction Stop)
    if ($Devices -eq 'virtio-scsi' -and -not ($drivers | Where-Object {$_.OriginalFileName -match 'vioscsi\.inf$'})) {
        throw 'VirtIO SCSI driver was not staged into the deployed Windows image.'
    }
    if ($Devices -eq 'vmware') {
        foreach ($name in @('pvscsi.inf','vmxnet3.inf')) {
            if (-not ($drivers | Where-Object {[IO.Path]::GetFileName($_.OriginalFileName) -ieq $name})) {
                throw "VMware target driver was not staged: $name"
            }
        }
    }
    & wpeutil.exe UpdateBootInfo | Out-Null
    $firmware = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control' -Name PEFirmwareType).PEFirmwareType
    $partitions = @(Get-Partition -DiskNumber 0)
    $system = if ($firmware -eq 2) {
        $partitions | Where-Object {$_.GptType -eq '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}'} | Select-Object -First 1
    } else {
        $partitions | Where-Object IsActive | Select-Object -First 1
    }
    if (-not $system) { throw 'System boot partition was not created.' }
    if (-not $system.DriveLetter) {
        Add-PartitionAccessPath -DiskNumber 0 -PartitionNumber $system.PartitionNumber -AccessPath 'S:\'
        $system = Get-Partition -DiskNumber 0 -PartitionNumber $system.PartitionNumber
    }
    $bootRoot = "$($system.DriveLetter):\"
    $bcd = if ($firmware -eq 2) {Join-Path $bootRoot 'EFI\Microsoft\Boot\BCD'} else {Join-Path $bootRoot 'Boot\BCD'}
    if (-not (Test-Path -LiteralPath $bcd)) { throw 'BCDBoot did not create the target BCD store.' }
    if ($firmware -eq 2 -and -not (Test-Path -LiteralPath (Join-Path $bootRoot 'EFI\Microsoft\Boot\bootmgfw.efi'))) {
        throw 'Deployed UEFI boot manager is missing.'
    }
    & reg.exe load HKLM\OSD_CI_SOFTWARE C:\Windows\System32\config\SOFTWARE | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the deployed Windows registry.' }
    try {
        $version = Get-ItemProperty 'HKLM:\OSD_CI_SOFTWARE\Microsoft\Windows NT\CurrentVersion'
        if ($version.EditionID -ne 'Professional') { throw 'Unexpected deployed Windows edition.' }
        if ($OS -eq 'windows11' -and [int]$version.CurrentBuildNumber -lt 22000) { throw 'Expected Windows 11.' }
        if ($OS -eq 'windows10' -and [int]$version.CurrentBuildNumber -ge 22000) { throw 'Expected Windows 10.' }
        $result = @{Completed=$true; GuardPassed=$guardPassed; OS=$OS; Build=$version.CurrentBuildNumber; Edition=$version.EditionID;
            Firmware=$firmware; BCD=$bcd; Partitions=$partitions.Count; KernelPresent=$true;
            Drivers=@($drivers | Where-Object {$_.OriginalFileName -match 'vioscsi|netkvm|pvscsi|vmxnet3'} | Select-Object Driver,OriginalFileName,Version)}
    }
    finally { & reg.exe unload HKLM\OSD_CI_SOFTWARE | Out-Null }
    Send-Report 'deployment' $result
    Write-Host 'OSDCLOUD FULL DEPLOYMENT PASS' -ForegroundColor Green
}
catch {
    Send-Report 'failure' @{Completed=$false; GuardPassed=$guardPassed; Error=$_.Exception.Message; Stack=$_.ScriptStackTrace;
        USBPartitions=@($Global:OSDCloud.USBPartitions | Select-Object DiskNumber,PartitionNumber,DriveLetter,AccessPaths);
        RecentErrors=@($Error | Select-Object -First 6 | ForEach-Object {
            @{Message=$_.Exception.Message; Type=$_.Exception.GetType().FullName; Stack=$_.ScriptStackTrace;
                Position=$_.InvocationInfo.PositionMessage; Target=[string]$_.TargetObject}
        })}
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
}
finally {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
    if ($guardPassed) { Send-Logs }
}
if ($result.Completed) { & wpeutil.exe Shutdown }
