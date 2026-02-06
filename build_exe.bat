@echo off
title Path Analyzer Editor - Build EXE
cd /d "%~dp0"

echo.
echo ============================================================
echo     PATH ANALYZER EDITOR v4.0 - Build Eseguibile
echo ============================================================
echo.
echo Directory: %CD%
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Python non trovato!
    pause
    exit /b 1
)
echo [OK] Python trovato:
python --version
echo.

echo [INFO] Installazione dipendenze...
pip install customtkinter --quiet --upgrade
pip install pyinstaller --quiet --upgrade
echo [OK] Dipendenze installate.
echo.

if not exist "path_analyzer_editor.py" (
    echo [ERRORE] path_analyzer_editor.py non trovato!
    dir /b
    pause
    exit /b 1
)
echo [OK] Sorgente trovato.
echo.

echo [INFO] Compilazione in corso (1-2 minuti)...
echo.

if exist "PathAnalyzerEditor.spec" (
    pyinstaller PathAnalyzerEditor.spec --clean --noconfirm
) else (
    pyinstaller --onefile --name PathAnalyzerEditor --noconsole --clean --noconfirm path_analyzer_editor.py
)

if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Compilazione fallita!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo     BUILD COMPLETATO!
echo ============================================================
echo.
echo Eseguibile: %CD%\dist\PathAnalyzerEditor.exe
echo.

if exist "build" rmdir /s /q "build"
echo [OK] Pulizia completata.
echo.
explorer "dist"
pause
