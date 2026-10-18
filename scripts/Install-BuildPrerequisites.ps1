#Requires -Version 5.1
#Requires -RunAsAdministrator
# This helper is used only on disposable GitHub-hosted build runners.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'This prerequisite installer only runs on a GitHub-hosted Actions runner.'
}
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$cache = Join-Path $env:RUNNER_TEMP 'netboot-adk'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$installers = @(
    @{
        File = 'adksetup.exe'
        Url = 'https://download.microsoft.com/download/8e0c0f5a-abb5-4358-a51b-168eb40b1590/adk/adksetup.exe'
        Sha256 = 'AC6A930FDB5C2980BA5FEFE606D47EDAAFCF5F647B4337411500D158EA77300F'
        Feature = 'OptionId.DeploymentTools'
    },
    @{
        File = 'adkwinpesetup.exe'
        Url = 'https://download.microsoft.com/download/a4a79e7a-f085-41c4-aebf-2538fd000790/adkwinpeaddons/adkwinpesetup.exe'
        Sha256 = 'D4DE67ACC83DE253CCC941DD0590808D83726BDD8EA768A374A7BEAFF7949D6A'
        Feature = 'OptionId.WindowsPreinstallationEnvironment'
    }
)
foreach ($installer in $installers) {
    $file = Join-Path $cache $installer.File
    Invoke-WebRequest -UseBasicParsing -Uri $installer.Url -OutFile $file
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $installer.Sha256) {
        throw 'ADK installer checksum mismatch.'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $file
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '^CN=Microsoft Corporation,') {
        throw 'ADK installer does not have a valid Microsoft signature.'
    }
    Write-Host ('Installing ' + $installer.File + ' on the disposable runner')
    $process = Start-Process -FilePath $file -ArgumentList @('/quiet', '/norestart', '/ceip', 'off', '/features', $installer.Feature) -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw ('ADK installation failed with code ' + $process.ExitCode) }
}
