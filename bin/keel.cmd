@echo off
rem keel's launcher for Windows (cmd and PowerShell): finds Python 3 and runs scripts\keel.py with the arguments.
rem The POSIX launcher is the file named keel beside this one.
setlocal
set "here=%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python -I "%here%..\scripts\keel.py" %*
  exit /b %errorlevel%
)
where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 -I "%here%..\scripts\keel.py" %*
  exit /b %errorlevel%
)
echo keel: Python 3 was not found on this machine (neither python nor python3). 1>&2
exit /b 2
