@echo off
REM Устанавливаем кодовую страницу UTF-8
chcp 65001
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo ====================================
echo Запуск Telegram бота поддержки
echo ====================================
echo.

REM Переход в директорию скрипта
pushd "%~dp0"

REM Проверка наличия виртуального окружения
if not exist "myenv312\Scripts\python.exe" (
    echo ОШИБКА: Виртуальное окружение myenv312 не найдено!
    echo.
    echo Создайте виртуальное окружение:
    echo   python -m venv myenv312
    echo.
    echo Или используйте существующее окружение.
    popd
    pause
    exit /b 1
)

echo Используется виртуальное окружение: myenv312
echo.

REM Активация окружения и запуск бота
call myenv312\Scripts\activate.bat
python bot.py

popd
pause

