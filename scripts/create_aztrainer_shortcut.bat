@echo off
set "SCRIPT_DIR=C:\azvision\trainer\scripts"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=AZ Trainer"

REM Delete existing shortcut if it exists
if exist "%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk" (
    echo Deleting existing shortcut...
    del "%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk"
    echo Existing shortcut deleted successfully.
)

REM Create a shortcut to the script on the desktop
echo Creating desktop shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo sLinkFile = "%DESKTOP_DIR%\%SHORTCUT_NAME%.lnk" >> "%TEMP%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut.vbs"
echo oLink.TargetPath = "%SCRIPT_DIR%\run_trainer.bat" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Save >> "%TEMP%\create_shortcut.vbs"
cscript /nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

echo Desktop shortcut created successfully.
exit /b 0
