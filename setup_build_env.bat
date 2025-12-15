@echo off
REM Скрипт для активации Build Tools и установки chromadb
REM Этот файл нужно запустить из Developer Command Prompt

echo ====================================
echo Установка ChromaDB с Build Tools
echo ====================================
echo.

REM Проверка наличия компилятора
where cl >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Компилятор cl.exe не найден!
    echo.
    echo Пожалуйста, запустите этот файл из Developer Command Prompt:
    echo - Нажмите Win+R
    echo - Введите: cmd
    echo - Найдите в меню Пуск: "Developer Command Prompt for VS"
    echo   или "x64 Native Tools Command Prompt"
    echo.
    pause
    exit /b 1
)

echo Компилятор найден!
echo.

REM Переход в директорию проекта (используем pushd для работы с кириллицей)
pushd "%~dp0"

REM Активация виртуального окружения
echo Активация виртуального окружения...
call myenv312\Scripts\activate.bat

REM Установка chromadb
echo.
echo Установка chromadb и sentence-transformers...
pip install chromadb==0.4.22 sentence-transformers

echo.
echo ====================================
if %ERRORLEVEL% EQU 0 (
    echo Установка завершена успешно!
) else (
    echo ОШИБКА при установке!
)
echo ====================================
popd
pause

