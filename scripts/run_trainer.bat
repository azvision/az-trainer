@echo off
set "PROJECT_DIR=C:\azvision\trainer"
set "TRAINER_SCRIPT=%PROJECT_DIR%\src\trainer.py"

REM Change directory to the project directory
cd /d "%PROJECT_DIR%" || (
    echo Failed to change directory to "%PROJECT_DIR%". Exiting...
    exit /b 1
)

REM Fetch latest changes from the remote repository
echo Fetching latest changes from the remote repository...
git fetch origin
if errorlevel 1 (
    echo Failed to fetch latest changes. Exiting...
    exit /b 1
)

REM Pull latest changes from the remote repository
echo Pulling latest changes from the remote repository...
git pull origin master
if errorlevel 1 (
    echo Failed to pull latest changes. Exiting...
    exit /b 1
)

REM Start the trainer script
echo Starting the trainer script...
start "" "%TRAINER_SCRIPT%"

exit /b 0
