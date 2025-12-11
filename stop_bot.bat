@echo off
echo Stopping all bot instances...
echo.
echo [INFO] Searching for Python processes running main.py...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" 2>nul
taskkill /F /IM python.exe /FI "COMMANDLINE eq *main.py*" 2>nul
timeout /t 2 /nobreak >nul
echo.
echo [OK] Done. You can now start the bot with: .\start_bot.bat
pause

