@echo off
set "PYTHON_VERSION=3.12.2"
set "GIT_INSTALLER_URL=https://github.com/git-for-windows/git/releases/download/v2.33.1.windows.1/PortableGit-2.33.1-64-bit.7z.exe"
set "GIT_INSTALLER=PortableGit-2.33.1-64-bit.7z.exe"
set "GIT_INSTALLER_PATH=%TEMP%\%GIT_INSTALLER%"

REM Check if Python 3.9 or greater is already installed
python --version | findstr /C:"Python 3" >nul
if %errorlevel% equ 0 (
    echo Python 3 is already installed. Skipping installation.
) else (
    REM Download Python installer
    echo Downloading Python installer...
    curl https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe -o python_install.exe

    REM Install Python quietly
    echo Installing Python...
    python_install.exe /quiet InstallAllUsers=1 PrependPath=1

    REM Cleanup: Delete the Python installer
    del "python_install.exe"

    echo Python installation completed.
)

REM Check if Git is already installed
git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Git is already installed. Skipping installation.
) else (
    REM Download and install Git
    @"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    choco install git
)

REM Check if both Python and Git are not installed
where python >nul 2>&1 && where git >nul 2>&1
if %errorlevel% equ 1 (
    echo Prerequisites installation completed successfully. Restarting...
    timeout /t 5 /nobreak >nul
    REM shutdown /r /t 0
) else (
    echo No prerequisites were installed. Exiting...
)

exit /b 0
