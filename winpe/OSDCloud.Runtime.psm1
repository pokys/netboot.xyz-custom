#Requires -Version 5.1
function Test-OSDCloudRequirements {
    [CmdletBinding()]
    param(
        [string]$ProbeUrl,
        [string]$ReportPath = (Join-Path $env:TEMP 'OSDCloud-Requirements.json'),
        [switch]$Offline
    )
    $ErrorActionPreference = 'Stop'
    if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\MiniNT')) {
        throw 'OSDCloud runtime validation is restricted to Windows PE.'
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $checks = New-Object 'Collections.Generic.List[object]'
    function Check([string]$Name, [scriptblock]$Action) {
        try {
            & $Action | Out-Null
            $checks.Add([pscustomobject]@{Name=$Name; Passed=$true; Error=$null})
            Write-Host "OK: $Name" -ForegroundColor DarkGray
        }
        catch {
            $checks.Add([pscustomobject]@{Name=$Name; Passed=$false; Error=$_.Exception.Message})
            Write-Host "FAILED: $Name - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Check 'PowerShell environment' {
        foreach ($name in @('ProgramData','USERPROFILE','LOCALAPPDATA','APPDATA','TEMP')) {
            $value = [Environment]::GetEnvironmentVariable($name)
            if (-not $value -or -not (Test-Path -LiteralPath $value)) { throw "Missing environment directory: $name" }
        }
    }
    Check 'OSD and package modules' {
        Import-Module PackageManagement -RequiredVersion '1.4.8.1' -Global -ErrorAction Stop
        Import-Module PowerShellGet -RequiredVersion '2.2.5' -Global -ErrorAction Stop
        Import-Module Microsoft.PowerShell.Archive -RequiredVersion '1.2.5' -Global -ErrorAction Stop
        Import-Module OSD -RequiredVersion '26.10.6.1' -Global -ErrorAction Stop
        Import-PackageProvider -Name NuGet -MinimumVersion '2.8.5.201' -ErrorAction Stop
    }
    Check 'Deployment commands' {
        foreach ($name in @('Start-OSDCloudGUI','Save-WebFile','Get-Disk','Get-Partition','New-Partition','Clear-Disk','Format-Volume',
            'Get-WindowsImage','Expand-WindowsImage','Add-WindowsDriver','Get-WindowsEdition','Get-CimInstance',
            'Compress-Archive','Expand-Archive','Get-FileHash','Invoke-WebRequest','bcdboot.exe','dism.exe','diskpart.exe',
            'reg.exe','expand.exe','wpeutil.exe','net.exe','robocopy.exe','manage-bde.exe','mountvol.exe','setx.exe','curl.exe','7za.exe')) {
            Get-Command -Name $name -ErrorAction Stop
        }
    }
    $work = Join-Path $env:TEMP ('OSDCloud-Check-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $work | Out-Null
    Check 'ZIP compression and extraction' {
        $source = New-Item -ItemType Directory -Path (Join-Path $work 'zip-source')
        'OSDCLOUD-ZIP-PASS' | Set-Content -LiteralPath (Join-Path $source.FullName 'probe.txt') -Encoding Ascii
        Compress-Archive -Path (Join-Path $source.FullName '*') -DestinationPath (Join-Path $work 'probe.zip')
        Expand-Archive -LiteralPath (Join-Path $work 'probe.zip') -DestinationPath (Join-Path $work 'zip-result')
        if ((Get-Content -LiteralPath (Join-Path $work 'zip-result\probe.txt') -Raw).Trim() -ne 'OSDCLOUD-ZIP-PASS') { throw 'ZIP content mismatch.' }
    }
    Check '7-Zip executable and extraction' {
        & "$env:SystemRoot\System32\7za.exe" x (Join-Path $work 'probe.zip') "-o$(Join-Path $work '7zip-result')" -y | Out-Null
        if ($LASTEXITCODE -ne 0 -or (Get-Content -LiteralPath (Join-Path $work '7zip-result\probe.txt') -Raw).Trim() -ne 'OSDCLOUD-ZIP-PASS') {
            throw '7-Zip could not extract the test archive.'
        }
    }
    Check 'curl executable' {
        & "$env:SystemRoot\System32\curl.exe" --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'curl.exe failed to start.' }
    }
    Check 'setx executable' {
        & "$env:SystemRoot\System32\setx.exe" /? | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'setx.exe failed to start.' }
    }
    Check 'DISM WIM metadata' {
        $wim = "$env:SystemRoot\System32\OSDCloud-test.wim"
        $metadata = Get-WindowsImage -ImagePath $wim -Index 1 -ErrorAction Stop
        if ($metadata.ImageName -ne 'OSDCloudRuntime') { throw 'Unexpected test WIM metadata.' }
        & "$env:SystemRoot\System32\dism.exe" /Get-WimInfo "/WimFile:$wim" /Index:1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Native DISM cannot read the test WIM.' }
    }
    Check 'Storage discovery' { Get-Disk -ErrorAction Stop }
    if (-not $Offline) {
        if (-not $ProbeUrl) {
            $manifest = Get-Content -LiteralPath "$env:SystemRoot\System32\osdcloud-runtime.json" -Raw | ConvertFrom-Json
            $ProbeUrl = $manifest.ProbeUrl
        }
        Check 'PowerShell Gallery lookup' {
            if (-not (Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue)) { Register-PSRepository -Default }
            Find-Module -Name OSD -RequiredVersion '26.10.6.1' -Repository PSGallery -ErrorAction Stop
        }
        Check 'OSD native download' {
            $result = Save-WebFile -SourceUrl $ProbeUrl -DestinationDirectory (Join-Path $work 'osd-native') -DestinationName probe.txt -Overwrite -ErrorAction Stop
            if (-not $result -or (Get-Content -LiteralPath $result.FullName -Raw).Trim() -ne 'OSDCLOUD-RUNTIME-DOWNLOAD-PASS') { throw 'Native OSD download content mismatch.' }
        }
        Check 'OSD WebClient download' {
            $result = Save-WebFile -SourceUrl $ProbeUrl -DestinationDirectory (Join-Path $work 'osd-webclient') -DestinationName probe.txt -Overwrite -WebClient -ErrorAction Stop
            if (-not $result -or (Get-Content -LiteralPath $result.FullName -Raw).Trim() -ne 'OSDCLOUD-RUNTIME-DOWNLOAD-PASS') { throw 'WebClient download content mismatch.' }
        }
        Check 'curl download with certificate validation' {
            $target = Join-Path $work 'curl-probe.txt'
            & "$env:SystemRoot\System32\curl.exe" --fail --location --silent --show-error --max-time 60 --output $target $ProbeUrl
            if ($LASTEXITCODE -ne 0 -or (Get-Content -LiteralPath $target -Raw).Trim() -ne 'OSDCLOUD-RUNTIME-DOWNLOAD-PASS') { throw 'curl download failed or content mismatch.' }
        }
    }
    $report = [pscustomobject]@{Passed=(@($checks | Where-Object {-not $_.Passed}).Count -eq 0); Checks=@($checks.ToArray())}
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
    if (-not $report.Passed) { throw "OSDCloud requirements check failed. See $ReportPath" }
    Write-Host 'OSDCloud requirements passed.' -ForegroundColor Green
    $report
}
Export-ModuleMember -Function Test-OSDCloudRequirements
