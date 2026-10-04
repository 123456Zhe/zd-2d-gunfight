@echo off
REM Launch ZD-2D-Gunfight with the project virtual environment.
REM No system Python or PATH change is required for this to work.
setlocal
set PYTHONUTF8=1
set "HERE=%~dp0"

if not exist "%HERE%.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at "%HERE%.venv"
    echo Create it with:  py -3.10 -m venv .venv
    echo Then install:    .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

"%HERE%.venv\Scripts\python.exe" "%HERE%main.py" %*
endlocal
