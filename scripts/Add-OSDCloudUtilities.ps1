#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$MountPath,
    [Parameter(Mandatory = $true)][string]$WorkPath
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not (Test-Path -LiteralPath (Join-Path $MountPath 'Windows\System32\wpeinit.exe'))) {
    throw 'Utilities may only be added to a mounted WinPE image.'
}
if (Test-Path -LiteralPath $WorkPath) { throw 'Utility work directory must be new.' }
New-Item -ItemType Directory -Path $WorkPath -Force | Out-Null
$system32 = Join-Path $MountPath 'Windows\System32'
$licenses = Join-Path $MountPath 'ProgramData\OSDCloud\Licenses'
New-Item -ItemType Directory -Path $licenses -Force | Out-Null
$sources = @(
    @{Name='curl'; Version='8.23.0_1'; File='curl.zip'; Url='https://curl.se/windows/dl-8.23.0_1/curl-8.23.0_1-win64-mingw.zip'; SHA256='752ff19c45be64af5b5f8d5222dce64e0f7b03d740a7362a4055c220fa9637c6'},
    @{Name='7-Zip'; Version='26.04'; File='7zip.7z'; Url='https://github.com/ip7z/7zip/releases/download/26.04/7z2604-extra.7z'; SHA256='dc4b11d3399db18b063630137145f5585d8f7ac847bf3639bd1185d7d1f7cee0'}
)
foreach ($source in $sources) {
    $file = Join-Path $WorkPath $source.File
    Invoke-WebRequest -UseBasicParsing -Uri $source.Url -OutFile $file
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $source.SHA256) {
        throw "Utility archive checksum mismatch: $($source.Name)"
    }
}
Expand-Archive -LiteralPath (Join-Path $WorkPath 'curl.zip') -DestinationPath (Join-Path $WorkPath 'curl')
$curlRoot = Join-Path $WorkPath 'curl\curl-8.23.0_1-win64-mingw'
foreach ($name in @('curl.exe', 'curl-ca-bundle.crt', 'libcurl-x64.dll')) {
    Copy-Item -LiteralPath (Join-Path $curlRoot "bin\$name") -Destination $system32
}
$curlLicense = New-Item -ItemType Directory -Path (Join-Path $licenses 'curl') -Force
Copy-Item -LiteralPath (Join-Path $curlRoot 'COPYING.txt') -Destination $curlLicense.FullName
Copy-Item -LiteralPath (Join-Path $curlRoot 'dep') -Destination $curlLicense.FullName -Recurse
# The extractor exists on the disposable GitHub Windows runner. It is not installed locally.
$extractor = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
if (-not (Test-Path -LiteralPath $extractor)) { throw 'The build runner needs its bundled 7-Zip extractor.' }
$extra = Join-Path $WorkPath '7zip'
& $extractor x (Join-Path $WorkPath '7zip.7z') "-o$extra" -y | Out-Host
if ($LASTEXITCODE -ne 0) { throw '7-Zip extraction failed.' }
foreach ($name in @('7za.exe', '7za.dll', '7zxa.dll')) {
    Copy-Item -LiteralPath (Join-Path $extra "x64\$name") -Destination $system32
}
$sevenLicense = New-Item -ItemType Directory -Path (Join-Path $licenses '7-Zip') -Force
Copy-Item -LiteralPath (Join-Path $extra 'License.txt') -Destination $sevenLicense.FullName
Copy-Item -LiteralPath (Join-Path $extra 'readme.txt') -Destination $sevenLicense.FullName
$setx = Join-Path $env:SystemRoot 'System32\setx.exe'
$signature = Get-AuthenticodeSignature -LiteralPath $setx
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft') {
    throw 'The runner setx.exe must have a valid Microsoft signature.'
}
Copy-Item -LiteralPath $setx -Destination $system32
$sources | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $MountPath 'ProgramData\OSDCloud\utilities.json') -Encoding UTF8
Write-Host 'Added pinned x64 curl, CA bundle, 7-Zip, Microsoft setx and licenses.'
