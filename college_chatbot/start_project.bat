@echo off
echo Starting... > start_log.txt
tasklist /FI "IMAGENAME eq ollama_app.exe" 2>NUL | find /I /N "ollama_app.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Ollama is running. >> start_log.txt
) else (
    echo Ollama is NOT running! >> start_log.txt
)

echo Installing dependencies... >> start_log.txt
pip install flask chainlit >> install.log 2>&1

echo Starting server... >> start_log.txt
python server.py >> server.log 2>&1
