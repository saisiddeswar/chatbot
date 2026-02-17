@echo off
echo ==================================================
echo   Starting College Chatbot System
echo ==================================================

REM 1. Check if Ollama is running (Try app, service, or port)
tasklist /FI "IMAGENAME eq ollama_app.exe" 2>NUL | find /I /N "ollama_app.exe">NUL
if "%ERRORLEVEL%"=="0" goto OLLAMA_OK

tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" goto OLLAMA_OK

curl -s http://127.0.0.1:11434 > NUL
if "%ERRORLEVEL%"=="0" goto OLLAMA_OK

:OLLAMA_FAIL
echo [WARN] Ollama is NOT running!
echo        Bot-3 will fallback to simple text extraction.
echo        To use Llama 3.2, please start Ollama first - e.g. 'ollama serve'
goto APP_START

:OLLAMA_OK
echo [OK] Ollama is running.

:APP_START
echo.
echo [START] Launching Flask Web Server...
echo         Open your browser to: http://127.0.0.1:5000
echo ==================================================

python server.py

pause
