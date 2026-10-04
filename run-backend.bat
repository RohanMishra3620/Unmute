@echo off
cd /d "%~dp0"
echo Installing dependencies...
pip install -r backend\requirements.txt
echo.
echo Starting backend on http://127.0.0.1:5000
echo Keep this window open. Open frontend in a second terminal.
echo.
set PYTHONPATH=%~dp0
python -m backend.app
pause
