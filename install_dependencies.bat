@echo off
chcp 65001 >nul
echo ========================================
echo Установка зависимостей для AI Support Bot
echo ========================================
echo.

REM Проверка виртуального окружения
if "%VIRTUAL_ENV%"=="" (
    echo ВНИМАНИЕ: Виртуальное окружение не активировано!
    echo Активируйте его командой: .venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)

echo Обновление pip...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Установка numpy с принудительным использованием wheel-файлов...
pip install --only-binary :all: numpy

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ОШИБКА: Не удалось установить numpy из готовых wheel-файлов.
    echo Возможные причины:
    echo 1. Python 3.14 слишком новый, wheel-файлов для него может не быть
    echo 2. Рекомендуется использовать Python 3.11 или 3.12
    echo.
    echo Попытка установки последней совместимой версии numpy...
    pip install "numpy<2.0.0" --prefer-binary
)

echo.
echo Установка остальных зависимостей...
pip install -r requirements.txt --prefer-binary

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Установка завершена успешно!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ОШИБКА при установке зависимостей!
    echo ========================================
    echo.
    echo Рекомендации:
    echo 1. Убедитесь, что используете Python 3.11 или 3.12 (не 3.14)
    echo 2. Проверьте подключение к интернету
    echo 3. Попробуйте обновить pip: python -m pip install --upgrade pip
    pause
    exit /b 1
)

pause
