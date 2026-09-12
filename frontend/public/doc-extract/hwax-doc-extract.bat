@echo off
rem HWAX document extractor - drag files or a folder onto this file.
setlocal
set "PS1=%~dp0hwax-doc-extract.ps1"
if not exist "%PS1%" (
  echo.
  echo   hwax-doc-extract.ps1 not found next to this file.
  echo   Download BOTH files into the SAME folder and try again.
  echo.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo.
  echo   No file given - running self test instead.
  echo   To extract: drag a PPT/Word/PDF/HTML file onto this .bat
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -SelfTest
  echo.
  pause
  exit /b %errorlevel%
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
echo.
pause
exit /b %errorlevel%
