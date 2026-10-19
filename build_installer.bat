@echo off
cd /d "%~dp0"

echo ========================================================
echo  Building MeetScript Setup Installer
echo ========================================================

echo.
echo [1/3] Ensuring PyInstaller is installed...
python -m pip install pyinstaller

echo.
echo [2/3] Compiling application with PyInstaller (MeetScript.exe with favicon.ico)...
python -m PyInstaller --noconfirm --onedir --windowed ^
  --name "MeetScript" ^
  --icon "favicon.ico" ^
  --add-data "favicon.ico;." ^
  --collect-all customtkinter ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all soundcard ^
  Transcript.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Compiling Windows Setup Installer with Inno Setup...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" installer.iss
) else (
    echo.
    echo Inno Setup CLI compiler not found at default path.
    echo You can open 'installer.iss' in the Inno Setup application and click 'Compile' (Ctrl+F9).
    pause
    exit /b 0
)

echo.
echo ========================================================
echo  BUILD COMPLETE!
echo  Installer is ready at:
echo  Transcriber\installer_output\MeetScript_Setup.exe
echo ========================================================
pause
