#Requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$DestinationPath)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$DestinationPath = [IO.Path]::GetFullPath($DestinationPath)
if (Test-Path -LiteralPath $DestinationPath) { throw 'Driver destination must be a new directory.' }
$manifestPath = Join-Path $PSScriptRoot 'winpe-physical-drivers.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$scratch = "$DestinationPath.download"
if (Test-Path -LiteralPath $scratch) { throw 'Driver download directory already exists.' }
New-Item -ItemType Directory -Path $scratch | Out-Null
New-Item -ItemType Directory -Path $DestinationPath | Out-Null
$cab = Join-Path $scratch 'drivers.cab'
Invoke-WebRequest -UseBasicParsing -Uri $manifest.url -OutFile $cab
if ((Get-FileHash -LiteralPath $cab -Algorithm SHA256).Hash -ne $manifest.sha256) {
    throw 'Physical driver pack SHA256 mismatch.'
}
$expanded = New-Item -ItemType Directory -Path (Join-Path $scratch 'expanded')
& "$env:SystemRoot\System32\expand.exe" '-F:*' $cab $expanded.FullName | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Physical driver CAB extraction failed.' }
$copied = @{}
foreach ($driver in $manifest.drivers) {
    $inf = Join-Path $expanded.FullName $driver.inf
    if ((Get-FileHash -LiteralPath $inf -Algorithm SHA256).Hash -ne $driver.infSHA256) {
        throw "Physical driver INF SHA256 mismatch: $($driver.name)"
    }
    $signature = Get-AuthenticodeSignature -LiteralPath (Join-Path (Split-Path $inf) $driver.catalog)
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=Microsoft Windows Hardware Compatibility Publisher,') {
        throw "Invalid Microsoft hardware catalog signature: $($driver.name)"
    }
    $text = Get-Content -LiteralPath $inf -Raw
    if ($text -notmatch '(?i)NTamd64' -or $text -notmatch [regex]::Escape($driver.version)) {
        throw "Unexpected physical driver architecture/version: $($driver.name)"
    }
    if ($driver.driverClass -notin @('Net', 'SCSIAdapter') -or
        $text -notmatch ('(?im)^\s*Class\s*=\s*' + [regex]::Escape($driver.driverClass) + '\s*(?:;.*)?$')) {
        throw "Unexpected physical driver class: $($driver.name)"
    }
    # Preserve each signed INF's companion files, but inject only allowlisted INFs.
    $relativeFolder = Split-Path $driver.inf
    if (-not $copied.ContainsKey($relativeFolder)) {
        $folder = New-Item -ItemType Directory -Path (Join-Path $DestinationPath $relativeFolder) -Force
        Get-ChildItem -LiteralPath (Split-Path $inf) -Force | Copy-Item -Destination $folder.FullName -Recurse -Force
        $copied[$relativeFolder] = $true
    }
}
Copy-Item -LiteralPath $manifestPath -Destination $DestinationPath
$bytes = (Get-ChildItem -LiteralPath $DestinationPath -File -Recurse | Measure-Object Length -Sum).Sum
if ($bytes -gt $manifest.maxPayloadBytes) { throw 'Selected physical drivers exceed the payload size budget.' }
Write-Host "Verified $($manifest.drivers.Count) selected physical driver packages; payload $bytes bytes."
