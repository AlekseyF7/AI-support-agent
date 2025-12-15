@echo off
chcp 65001 >nul
echo ====================================
echo Установка ChromaDB
echo ====================================
echo.

REM Используем pushd вместо cd для работы с путями, содержащими кириллицу
pushd "%~dp0"

echo Проверка компилятора...
where cl >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ВНИМАНИЕ: Компилятор cl.exe не найден!
    echo Убедитесь, что вы запустили этот файл из Developer Command Prompt
    echo.
)

echo Текущая директория: %CD%
echo.

echo Активация виртуального окружения...
call myenv312\Scripts\activate.bat

echo.
echo Установка chromadb и sentence-transformers...
pip install chromadb==0.4.22 sentence-transformers

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo Установка завершена успешно!
    echo ====================================
) else (
    echo.
    echo ====================================
    echo ОШИБКА при установке!
    echo Проверьте, что вы используете Developer Command Prompt
    echo ====================================
)

popd
pause

