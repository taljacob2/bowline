@echo off
rem keel's launcher for Windows (cmd and PowerShell): finds Python 3 and runs scripts\keel.py with the arguments,
rem passing its exit code on. The POSIX launcher is the file named keel beside this one.
setlocal
set "here=%~dp0"
where python >nul 2>nul
if not errorlevel 1 goto :python
where python3 >nul 2>nul
if not errorlevel 1 goto :python3
echo keel: Python 3 was not found on this machine (neither python nor python3). 1>&2
exit /b 2

:python
python -I "%here%..\scripts\keel.py" %*
exit /b %errorlevel%

:python3
python3 -I "%here%..\scripts\keel.py" %*
exit /b %errorlevel%
