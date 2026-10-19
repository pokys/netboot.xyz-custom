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
$file = Join-Path $ModuleRoot 'Public\Functions\Save-WebFile.ps1'
$originalHash = 'f593114130baaba0f5dc4e7f840cf8a9d84a0e1d7ef82226983ab74cb8b1b1cc'
$patchedHash = '0bb1315eeded3f317e9e5c70f4eff483a6a1a3fe7085de60eb1c992558ee3ff3'
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $actualHash = ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($file)))).Replace('-', '').ToLowerInvariant()
}
finally { $sha.Dispose() }
if ($actualHash -eq $patchedHash) {
    Write-Host 'OSD WebClient repair is already applied.'
    return
}
if ($actualHash -ne $originalHash) {
    throw 'Unexpected OSD Save-WebFile source. Refusing to patch a different version.'
}
# Keep the public -WebClient switch. Rename only the three local client uses.
$content = [IO.File]::ReadAllText($file)
$content = $content.Replace('$WebClient = New-Object System.Net.WebClient', '$downloadClient = New-Object System.Net.WebClient')
$content = $content.Replace('$WebClient.DownloadFile(', '$downloadClient.DownloadFile(')
$content = $content.Replace('$WebClient.Dispose()', '$downloadClient.Dispose()')
$encoding = New-Object Text.UTF8Encoding($false)
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $newHash = ([BitConverter]::ToString($sha.ComputeHash($encoding.GetBytes($content)))).Replace('-', '').ToLowerInvariant()
}
finally { $sha.Dispose() }
if ($newHash -ne $patchedHash) { throw 'Patched source checksum mismatch; original file was not modified.' }
[IO.File]::WriteAllText($file, $content, $encoding)
Write-Host 'Repaired OSD Save-WebFile WebClient fallback. Restart the launcher to load the corrected function.'
