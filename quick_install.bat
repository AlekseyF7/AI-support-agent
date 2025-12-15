@echo off
chcp 65001 >nul 2>&1
REM Простой скрипт установки chromadb
REM Запустите из Developer Command Prompt

echo Установка ChromaDB...
echo.

REM Переход в директорию скрипта
pushd "%~dp0"

REM Активация виртуального окружения
if exist "myenv312\Scripts\activate.bat" (
    call myenv312\Scripts\activate.bat
    echo Виртуальное окружение активировано
) else (
    echo ОШИБКА: Виртуальное окружение myenv312 не найдено!
    popd
    pause
    exit /b 1
)

echo.
echo Установка пакетов...
pip install chromadb==0.4.22 sentence-transformers

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Установка завершена успешно!
) else (
    echo.
    echo ОШИБКА при установке!
    echo Убедитесь, что вы используете Developer Command Prompt
)

popd
pause

