@echo off
set "PROJECT_DIR=c:\azvision\trainer"
set "REQUIREMENTS_FILE=requirements.txt"
set "VENV_NAME=.venv"
set "GIT_REPO=https://github.com/azvision/az-trainer.git"

REM Clone the GitHub repository
echo Cloning GitHub repository...
git clone "%GIT_REPO%" "%PROJECT_DIR%"
if errorlevel 1 (
    echo Failed to clone the GitHub repository. Exiting...
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv "%PROJECT_DIR%\%VENV_NAME%"
if errorlevel 1 (
    echo Failed to create virtual environment. Exiting...
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call "%PROJECT_DIR%\%VENV_NAME%\Scripts\activate.bat"

REM Install project dependencies
echo Installing project dependencies...
pip install -r "%PROJECT_DIR%\%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo Failed to install project dependencies. Exiting...
    exit /b 1
)

echo az-trainer installation completed successfully.
exit /b 0
