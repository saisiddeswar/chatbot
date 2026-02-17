@echo off
cls
echo ==================================================
echo       OLLAMA STATUS CHECKER (DIAGNOSTIC)
echo ==================================================
echo.

echo 1. Checking system path for 'ollama' command...
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] 'ollama' command not found in PATH.
    echo        Is Ollama installed? Download from https://ollama.com
    goto END
) else (
    echo [PASS] 'ollama' command found.
)
echo.

echo 2. Checking for running process (ollama_app.exe)...
tasklist /FI "IMAGENAME eq ollama_app.exe" 2>NUL | find /I /N "ollama_app.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [PASS] ollama_app.exe is running (System Tray).
) else (
    echo [FAIL] ollama_app.exe is NOT running.
)

echo 3. Checking for running service (ollama.exe)...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [PASS] ollama.exe is running (Background Service).
) else (
    echo [FAIL] ollama.exe is NOT running.
)
echo.

echo 4. Checking if Port 11434 is responding...
curl -s http://127.0.0.1:11434 > NUL
if "%ERRORLEVEL%"=="0" (
    echo [PASS] Port 11434 is accepting connections.
) else (
    echo [FAIL] Port 11434 is NOT responding.
)
echo.

echo ==================================================
echo                  SUMMARY
echo ==================================================
echo If any checks above show [PASS], Ollama is working.
echo If ALL checks show [FAIL], you must start Ollama.
echo.
echo TO START OLLAMA MANUALLY:
echo 1. Open a NEW terminal window.
echo 2. Type: 'ollama serve'
echo 3. Keep that window OPEN.
echo 4. Return here and run 'check_ollama_status.bat' again.
echo ==================================================
echo.
pause
