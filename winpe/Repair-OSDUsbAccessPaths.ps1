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
$patchedHash = '11dffe2035ca0083a9704b1241c7682221ed98f59296968528f74639bb0382b4'
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
$encoding = New-Object Text.UTF8Encoding($false)
if ((Get-SourceHash ($encoding.GetBytes($content))) -ne $patchedHash) {
    throw 'Patched source checksum mismatch; original file was not modified.'
}
[IO.File]::WriteAllText($file, $content, $encoding)
Write-Host 'Repaired OSD boot USB drive-letter removal and restoration paths.'
