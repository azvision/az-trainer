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
    REM Install Python
    echo Installing Python %PYTHON_VERSION%...
    python-%PYTHON_VERSION%.exe /quiet InstallAllUsers=1 PrependPath=1
    if errorlevel 1 (
        echo Failed to install Python. Exiting...
        exit /b 1
    )
)

REM Check if Git is already installed
git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Git is already installed. Skipping installation.
) else (
    REM Download and install portable Git
    echo Downloading Git...
    bitsadmin.exe /transfer GitDownload /priority high %GIT_INSTALLER_URL% "%GIT_INSTALLER_PATH%"
    echo Installing Git...
    "%GIT_INSTALLER_PATH%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    if errorlevel 1 (
        echo Failed to install Git. Exiting...
        exit /b 1
    )
)

REM Check if either Python or Git was installed, and restart if necessary
python --version >nul 2>&1 || git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Prerequisites installation completed successfully. Restarting...
    REM timeout /t 5 /nobreak >nul
    REM shutdown /r /t 0
) else (
    echo No prerequisites were installed. Exiting...
)

exit /b 0
