@echo off
title Intrinsic Value API Server
echo ============================================================
echo   True Value Finder - Intrinsic Value Calculator
echo   Starting API server on http://localhost:5000
echo ============================================================
echo.
echo Opening browser... The page will connect automatically once
echo the server is ready. Press Ctrl+C here to stop the server.
echo.
cd /d "%~dp0"
call venv\Scripts\activate.bat

:: Open the browser immediately — the page will auto-retry until the server is up
start "" "%~dp0index.html"

:: Start the server (blocking — keeps this window open)
python api_server.py
pause
