@echo off
wpeinit
if errorlevel 1 goto failed
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File X:\Windows\System32\Start-Install.ps1
if errorlevel 1 goto failed
goto end
:failed
echo OSDCloud could not start. Check network, drivers, and the error above.
:end
echo Returned to WinPE. Type exit to close this command prompt.
