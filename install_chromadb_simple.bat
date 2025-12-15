@echo off
chcp 65001 >nul
echo ====================================
echo Installing ChromaDB
echo ====================================
echo.

REM Установка chromadb
echo Installing chromadb and sentence-transformers...
call myenv312\Scripts\activate.bat
pip install chromadb==0.4.22 sentence-transformers

echo.
if %ERRORLEVEL% EQU 0 (
    echo Installation completed successfully!
) else (
    echo ERROR during installation!
    echo.
    echo If you see compilation errors, make sure you are running this
    echo from Developer Command Prompt for Visual Studio.
    echo.
    echo To open Developer Command Prompt:
    echo 1. Press Win+R
    echo 2. Type: cmd
    echo 3. Find "Developer Command Prompt for VS" in Start menu
    echo.
)
echo ====================================
pause

