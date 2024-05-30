@echo off
set "PROJECT_DIR=C:\azvision\trainer"
set "TRAINER_SCRIPT=%PROJECT_DIR%\src\trainer.py"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "REQUIREMENTS_FILE=%PROJECT_DIR%\requirements.txt"

REM Change directory to the project directory
cd /d "%PROJECT_DIR%" || (
    echo Failed to change directory to "%PROJECT_DIR%". Exiting...
    exit /b 1
)

REM Activate the virtual environment
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM Fetch latest changes from the remote repository
echo Fetching latest changes from the remote repository...
git fetch origin
if errorlevel 1 (
    echo Failed to fetch latest changes. Exiting...
    exit /b 1
)

REM Pull latest changes from the remote repository
echo Pulling latest changes from the remote repository...
git pull origin production
if errorlevel 1 (
    echo Failed to pull latest changes. Exiting...
    exit /b 1
)

REM Install packages from requirements.txt
echo Installing packages from requirements.txt...
pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo Failed to install packages. Exiting...
    exit /b 1
)

REM Start the trainer script
echo Starting the trainer script...
python "%TRAINER_SCRIPT%"

exit /b 0
