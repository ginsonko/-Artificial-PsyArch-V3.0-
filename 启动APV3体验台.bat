@echo off
cd /d %~dp0
echo ========================================
echo   APV3 Open Dialogue Foundation
echo ========================================
echo.
echo Starting web server on port 8765...
echo Browser will open automatically.
echo Press Ctrl+C to stop.
echo.
python -m apv3test.web_chat --port 8765 --open
pause