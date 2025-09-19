@echo off
set VENV_DIR=venv

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
) else (
    echo Virtual environment already exists.
)

call %VENV_DIR%\Scripts\activate
if ERRORLEVEL 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

python -m pip install --upgrade pip

pip install --upgrade pytubefix pydub pillow

echo Running gui.py...
python gui.py

echo Done!
pause



