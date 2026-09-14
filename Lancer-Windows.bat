@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
where py >nul 2>nul
if errorlevel 1 (
  echo Installe Python 3.11 ou plus recent avec le lanceur py, puis relance ce fichier.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto failed
:run
".venv\Scripts\python.exe" -c "import mailbox_sync, PySide6" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -e .
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m mailbox_sync
if errorlevel 1 goto failed
exit /b 0
:failed
echo Le lancement a echoue. Consulte le message ci-dessus et README.md.
pause
exit /b 1
