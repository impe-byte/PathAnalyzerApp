@echo off
title Path Analyzer - Build EXE GUI

:: Sposta la directory di lavoro nella cartella dove si trova questo .bat
cd /d "%~dp0"

echo.
echo ============================================================
echo     PATH ANALYZER GUI - Build Eseguibile Windows
echo ============================================================
echo.
echo Directory di lavoro: %CD%
echo.

:: --- Controlla Python ---
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Python non trovato!
    echo          Installa Python 3.8+ da: https://www.python.org/downloads/
    echo          IMPORTANTE: spunta "Add Python to PATH" durante l installazione.
    pause
    exit /b 1
)
echo [OK] Python trovato:
python --version
echo.

:: --- Installa dipendenze ---
echo [INFO] Installazione dipendenze...
pip install customtkinter --quiet --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Installazione customtkinter fallita.
    pause
    exit /b 1
)
pip install pyinstaller --quiet --upgrade
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Installazione pyinstaller fallita.
    pause
    exit /b 1
)
echo [OK] Dipendenze installate.
echo.

:: --- Controlla file sorgente ---
if not exist "path_analyzer_gui.py" (
    echo [ERRORE] File path_analyzer_gui.py non trovato!
    echo          File presenti nella cartella:
    dir /b
    echo.
    echo          Assicurati che path_analyzer_gui.py sia nella stessa cartella di questo .bat
    pause
    exit /b 1
)
echo [OK] File path_analyzer_gui.py trovato.
echo.

:: --- Build ---
echo [INFO] Compilazione in corso...
echo        Questo puo richiedere 1-2 minuti...
echo.

if exist "PathAnalyzer.spec" (
    echo [INFO] Uso file .spec personalizzato...
    pyinstaller PathAnalyzer.spec --clean --noconfirm
) else (
    echo [INFO] Build standard...
    pyinstaller --onefile --name PathAnalyzer --noconsole --clean --noconfirm path_analyzer_gui.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Compilazione fallita!
    echo.
    echo Suggerimenti:
    echo   1. Assicurati che l antivirus non blocchi PyInstaller
    echo   2. Prova: pip install pyinstaller --upgrade --force-reinstall
    echo   3. Controlla il log sopra per dettagli
    pause
    exit /b 1
)

echo.
echo ============================================================
echo     BUILD COMPLETATO!
echo ============================================================
echo.
echo Eseguibile creato in:
echo   %CD%\dist\PathAnalyzer.exe
echo.

:: --- Pulizia ---
echo [INFO] Pulizia file temporanei...
if exist "build" rmdir /s /q "build"
echo [OK] Pulizia completata.
echo.

:: --- Apri cartella ---
echo Apro la cartella con l eseguibile...
explorer "dist"
echo.
pause
