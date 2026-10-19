#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$DestinationPath
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$DestinationPath = [IO.Path]::GetFullPath($DestinationPath)
if (Test-Path -LiteralPath $DestinationPath) { throw 'Driver destination must be a new directory.' }
New-Item -ItemType Directory -Path $DestinationPath | Out-Null
$drivers = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'winpe-virtual-drivers.json') -Raw | ConvertFrom-Json
foreach ($driver in $drivers) {
    $folder = New-Item -ItemType Directory -Path (Join-Path $DestinationPath $driver.name)
    $cab = Join-Path $folder.FullName 'driver.cab'
    Write-Host "Downloading $($driver.name) $($driver.version) from Microsoft Update Catalog"
    Invoke-WebRequest -UseBasicParsing -Uri $driver.url -OutFile $cab
    if ((Get-FileHash -LiteralPath $cab -Algorithm SHA256).Hash -ne $driver.sha256) {
        throw "Driver SHA256 mismatch: $($driver.name)"
    }
    & "$env:SystemRoot\System32\expand.exe" '-F:*' $cab $folder.FullName | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Driver CAB extraction failed: $($driver.name)" }
    $inf = Join-Path $folder.FullName $driver.inf
    $catalog = Join-Path $folder.FullName $driver.catalog
    if (-not (Test-Path -LiteralPath $inf) -or -not (Test-Path -LiteralPath $catalog)) {
        throw "Expected INF/catalog missing: $($driver.name)"
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $catalog
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=Microsoft Windows Hardware Compatibility Publisher,') {
        throw "Invalid Microsoft hardware catalog signature: $($driver.name)"
    }
    $infText = Get-Content -LiteralPath $inf -Raw
    if ($infText -notmatch '(?i)NTamd64' -or $infText -notmatch [regex]::Escape($driver.version)) {
        throw "Unexpected driver architecture/version: $($driver.name)"
    }
    # Some CABs contain additional optional drivers. Only inject the selected INF.
    Get-ChildItem -LiteralPath $folder.FullName -Filter '*.inf' | Where-Object Name -ne $driver.inf |
        Remove-Item -Force
    Remove-Item -LiteralPath $cab
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'winpe-virtual-drivers.json') -Destination $DestinationPath
Write-Host "Verified virtual machine drivers ready: $DestinationPath"
