@echo off
cd /d "%~dp0frontend"
echo Starting frontend on http://127.0.0.1:5500
echo Open this URL in your browser (do NOT use [::] or port 5000):
echo.
echo    http://127.0.0.1:5500
echo.
echo Keep this window open.
python -m http.server 5500 --bind 127.0.0.1
pause
