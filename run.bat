@echo off
rem Run from this file's own folder, whatever drive or folder it was started from.
cd /d "%~dp0" || exit /b 1
python add_new_event.py
set "rc=%errorlevel%"
pause
exit /b %rc%
