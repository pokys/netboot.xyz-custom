#Requires -Version 5.1
[CmdletBinding()]
param([string]$ModuleRoot)
$ErrorActionPreference = 'Stop'
if (-not $ModuleRoot) {
    if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT')) {
        throw 'Without an explicit offline ModuleRoot this repair may only run inside Windows PE.'
    }
    $ModuleRoot = Join-Path $env:ProgramFiles 'WindowsPowerShell\Modules\OSD\26.10.6.1'
}
$file = Join-Path $ModuleRoot 'Private\Invoke-OSDCloudGUI.ps1'
$originalHash = '877a567ddd33eb645eb3dc2df22cfe2bce2253c4cd1ba714f48eef18b4a31a2c'
$patchedHash = '00cfa2a5e27718157c828db98ffa4204c6a9c4e5cc5c4763e6d10ce13ffcc1ff'
function Get-SourceHash([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
$actualHash = Get-SourceHash ([IO.File]::ReadAllBytes($file))
if ($actualHash -eq $patchedHash) {
    Write-Host 'OSD USB access path repair is already applied.'
    return
}
if ($actualHash -ne $originalHash) {
    throw 'Unexpected OSD Invoke-OSDCloudGUI source. Refusing to patch a different version.'
}
$content = [IO.File]::ReadAllText($file)
$newline = if ($content.Contains("`r`n")) {"`r`n"} else {"`n"}
# Normalize mounted volume roots to D:\. Unmounted USB partitions have no
# letter to remove or restore and must not be assigned one by this step.
$content = $content.Replace('AccessPath = "$($USBPartition.DriveLetter):"', 'AccessPath = "$($USBPartition.DriveLetter):\"')
foreach ($needle in @('                    $RemovePartitionAccessPath = @{', '                    $ParamAddPartitionAccessPath = @{')) {
    $guard = '                    if ([string]$USBPartition.DriveLetter -notmatch ''^[A-Za-z]$'') { continue }'
    $content = $content.Replace($needle, $guard + $newline + $needle)
}
$remove = @'
                    try {
                        Remove-PartitionAccessPath @RemovePartitionAccessPath -ErrorAction Stop
                    }
                    catch {
                        if ((Get-Disk -Number $USBPartition.DiskNumber -ErrorAction Stop).BusType -ne 'USB') { throw }
                        $usbRoot = $RemovePartitionAccessPath.AccessPath
                        Write-Host "Storage CIM could not remove USB $usbRoot; using mountvol."
                        & "$env:SystemRoot\System32\mountvol.exe" $usbRoot /D | Out-Host
                        if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $usbRoot)) {
                            throw "Could not remove USB access path $usbRoot."
                        }
                    }
'@
$restore = @'
                    try {
                        Add-PartitionAccessPath @ParamAddPartitionAccessPath -ErrorAction Stop
                    }
                    catch {
                        if ((Get-Disk -Number $USBPartition.DiskNumber -ErrorAction Stop).BusType -ne 'USB') { throw }
                        $usbVolume = $USBPartition.AccessPaths | Where-Object {
                            $_.StartsWith('\\?\Volume{') -and $_.EndsWith('}\')
                        } | Select-Object -First 1
                        if (-not $usbVolume) { throw 'USB volume identity is unavailable for restoring its access path.' }
                        $usbRoot = $null
                        foreach ($code in 68..90) {
                            if ($code -eq 88) { continue }
                            $candidate = "$([char]$code):\"
                            if (-not (Test-Path -LiteralPath $candidate)) { $usbRoot = $candidate; break }
                        }
                        if (-not $usbRoot) { throw 'No free drive letter is available for the USB volume.' }
                        Write-Host "Storage CIM could not restore USB $usbVolume; using mountvol at $usbRoot."
                        & "$env:SystemRoot\System32\mountvol.exe" $usbRoot $usbVolume | Out-Host
                        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $usbRoot)) {
                            throw "Could not restore USB access path $usbRoot."
                        }
                    }
                    Start-Sleep -Seconds 5
'@
$remove = $remove.Replace("`r`n", "`n").Replace("`n", $newline)
$restore = $restore.Replace("`r`n", "`n").Replace("`n", $newline)
$content = $content.Replace('                    Remove-PartitionAccessPath @RemovePartitionAccessPath -ErrorAction Stop', $remove)
$content = $content.Replace('                    Add-PartitionAccessPath @ParamAddPartitionAccessPath; Start-Sleep -Seconds 5', $restore)
$encoding = New-Object Text.UTF8Encoding($false)
if ((Get-SourceHash ($encoding.GetBytes($content))) -ne $patchedHash) {
    throw 'Patched source checksum mismatch; original file was not modified.'
}
[IO.File]::WriteAllText($file, $content, $encoding)
Write-Host 'Repaired OSD boot USB drive-letter removal and restoration paths.'
