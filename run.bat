@echo off
set VENV_DIR=venv

REM 가상환경 생성
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
) else (
    echo Virtual environment already exists.
)

REM 가상환경 활성화
call %VENV_DIR%\Scripts\activate.bat
if ERRORLEVEL 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

REM pip 업그레이드
python -m pip install --upgrade pip

pip install --upgrade pytubefix pydub pillow

REM 스크립트 실행
echo Running hoi4_music_generator.py...
python hoi4_music_generator.py

echo Done!
pause

