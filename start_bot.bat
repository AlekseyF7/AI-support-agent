@echo off
chcp 65001 >nul
echo Starting Telegram Support Bot...
echo.

REM Проверка виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please run setup_venv.bat first or create venv manually.
    pause
    exit /b 1
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

echo [INFO] If you see "Conflict" error, stop the bot first with: stop_bot.bat
echo.
python main.py

if errorlevel 1 (
    echo.
    echo Bot stopped with error!
    pause
)

