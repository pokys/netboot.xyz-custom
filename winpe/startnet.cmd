@echo off
rem PowerShellGet needs profile/data paths that plain ADK WinPE may omit.
if not defined USERPROFILE set "USERPROFILE=%SystemRoot%\System32\config\systemprofile"
if not defined ProgramData set "ProgramData=%SystemDrive%\ProgramData"
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
if not defined APPDATA set "APPDATA=%USERPROFILE%\AppData\Roaming"
if not exist "%ProgramData%" mkdir "%ProgramData%"
if not exist "%LOCALAPPDATA%" mkdir "%LOCALAPPDATA%"
if not exist "%APPDATA%" mkdir "%APPDATA%"
if not exist "%USERPROFILE%\Documents" mkdir "%USERPROFILE%\Documents"
if exist "%SystemRoot%\System32\curl-ca-bundle.crt" set "CURL_CA_BUNDLE=%SystemRoot%\System32\curl-ca-bundle.crt"
wpeinit
if errorlevel 1 goto failed
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File X:\Windows\System32\Start-Install.ps1
if errorlevel 1 goto failed
goto end
:failed
echo OSDCloud could not start. Check network, drivers, and the error above.
:end
echo Returned to WinPE. Type exit to close this command prompt.
