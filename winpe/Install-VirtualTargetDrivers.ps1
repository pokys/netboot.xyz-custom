#Requires -Version 5.1
# OSDCloud Config/Scripts/Shutdown hook, after applying the selected Windows image.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT')) {
    throw 'Offline virtual drivers may only be added from Windows PE.'
}
if (-not $Global:OSDCloud.IsWinPE -or $Global:OSDCloud.ExpandWindowsImage.ApplyPath -ne 'C:\' -or
    -not (Test-Path -LiteralPath 'C:\Windows\System32\ntoskrnl.exe')) {
    throw 'Virtual target drivers require an OSDCloud-applied Windows image at C:\.'
}
$devices = @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop | Select-Object -ExpandProperty DeviceID)
$families = @()
if ($devices -match 'PCI\\VEN_1AF4&') { $families += 'VirtIO-*' }
if ($devices -match 'PCI\\VEN_15AD&') { $families += 'VMware-*' }
if ($families.Count -eq 0) {
    Write-Host 'No supported virtual hardware found; skipping virtual target drivers.'
    return
}
$root = Join-Path $env:ProgramData 'OSDCloud\VirtualDrivers'
$manifest = Get-Content -LiteralPath (Join-Path $root 'winpe-virtual-drivers.json') -Raw | ConvertFrom-Json
$targetBuild = [Diagnostics.FileVersionInfo]::GetVersionInfo('C:\Windows\System32\ntoskrnl.exe').FileBuildPart
$selected = @($manifest | Where-Object {
    $name = $_.name
    @($families | Where-Object { $name -like $_ }).Count -gt 0 -and
        (-not $_.targetMinBuild -or $targetBuild -ge $_.targetMinBuild) -and
        (-not $_.targetMaxBuild -or $targetBuild -le $_.targetMaxBuild)
})
if ($selected.Count -eq 0) { throw 'Virtual hardware was detected but its signed driver payload is missing.' }
foreach ($driver in $selected) {
    $folder = Join-Path $root $driver.name
    if (-not (Test-Path -LiteralPath (Join-Path $folder $driver.inf))) {
        throw "Missing target driver: $($driver.name)"
    }
    Write-Host "Adding signed $($driver.name) $($driver.version) to deployed Windows..."
    Add-WindowsDriver -Path 'C:\' -Driver $folder -Recurse -ErrorAction Stop | Out-Null
}
$installed = @(Get-WindowsDriver -Path 'C:\' -All -ErrorAction Stop)
foreach ($driver in $selected) {
    if (-not ($installed | Where-Object {
        [IO.Path]::GetFileName($_.OriginalFileName) -ieq $driver.inf -and $_.Version -eq $driver.version
    })) { throw "Target driver verification failed: $($driver.name)" }
}
$report = @($selected | Select-Object name,version,inf)
$logs = New-Item -ItemType Directory -Path 'C:\Windows\Temp\osdcloud-logs' -Force
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $logs.FullName 'VirtualTargetDrivers.json') -Encoding UTF8
Write-Host 'Virtual storage and network drivers are staged for the installed Windows boot.' -ForegroundColor Green
