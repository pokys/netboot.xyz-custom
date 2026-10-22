#Requires -Version 5.1
# OSDCloud post-apply hook: carry matching storage/LAN drivers into Windows.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT') -or
    -not $Global:OSDCloud.IsWinPE -or $Global:OSDCloud.ExpandWindowsImage.ApplyPath -ne 'C:\' -or
    -not (Test-Path -LiteralPath 'C:\Windows\System32\ntoskrnl.exe')) {
    throw 'Physical target drivers require Windows PE and an OSDCloud-applied image at C:\.'
}
$root = Join-Path $env:ProgramData 'OSDCloud\PhysicalDrivers'
$manifest = Get-Content -LiteralPath (Join-Path $root 'winpe-physical-drivers.json') -Raw | ConvertFrom-Json
$targetBuild = [Diagnostics.FileVersionInfo]::GetVersionInfo('C:\Windows\System32\ntoskrnl.exe').FileBuildPart
$candidates = @($manifest.drivers | Where-Object {
    $targetBuild -ge $_.targetMinBuild -and (-not $_.targetMaxBuild -or $targetBuild -le $_.targetMaxBuild)
})
$models = @{}
foreach ($driver in $candidates) {
    $inf = Join-Path $root $driver.inf
    if ((Get-FileHash -LiteralPath $inf -Algorithm SHA256).Hash -ne $driver.infSHA256) {
        throw "Physical target INF SHA256 mismatch: $($driver.name)"
    }
    $ids = @{}
    foreach ($line in (Get-Content -LiteralPath $inf)) {
        # Model entries: description = install-section, hardware-id[, compatible-id].
        if ($line -match '^\s*[^;=]+\s*=\s*[^,;]+,\s*(?:PCI|USB)\\') {
            $fields = ($line -split ';', 2)[0].Split('=', 2)[1].Split(',')
            foreach ($field in $fields[1..($fields.Count - 1)]) {
                $id = $field.Trim().Trim('"')
                if ($id -match '^(?:PCI|USB)\\') { $ids[$id] = $true }
            }
        }
    }
    $models[$driver.name] = $ids
}
$selected = @{}
foreach ($device in @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop)) {
    # HardwareID/CompatibleID are ordered from specific to generic by PnP.
    $ids = @($device.HardwareID) + @($device.CompatibleID)
    $matches = foreach ($driver in $candidates) {
        for ($rank = 0; $rank -lt $ids.Count; $rank++) {
            if ($ids[$rank] -and $models[$driver.name].ContainsKey([string]$ids[$rank])) {
                [pscustomobject]@{ Rank = $rank; Version = [version]$driver.version; Driver = $driver }
                break
            }
        }
    }
    $best = $matches | Sort-Object @{Expression = 'Rank'; Ascending = $true}, @{Expression = 'Version'; Descending = $true} | Select-Object -First 1
    if ($best) { $selected[$best.Driver.name] = $best.Driver }
}
if ($selected.Count -eq 0) {
    Write-Host 'No matching physical storage or LAN hardware; skipping physical target drivers.'
    return
}
foreach ($driver in $selected.Values) {
    Write-Host "Adding matching signed $($driver.name) $($driver.version) to deployed Windows..."
    Add-WindowsDriver -Path 'C:\' -Driver (Join-Path $root $driver.inf) -ErrorAction Stop | Out-Null
}
$installed = @(Get-WindowsDriver -Path 'C:\' -All -ErrorAction Stop)
foreach ($driver in $selected.Values) {
    if (-not ($installed | Where-Object {
        [IO.Path]::GetFileName($_.OriginalFileName) -ieq [IO.Path]::GetFileName($driver.inf) -and
            [version]$_.Version -eq [version]$driver.version
    })) { throw "Physical target driver verification failed: $($driver.name)" }
}
$logs = New-Item -ItemType Directory -Path 'C:\Windows\Temp\osdcloud-logs' -Force
@($selected.Values | Select-Object name,version,inf) | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $logs.FullName 'PhysicalTargetDrivers.json') -Encoding UTF8
