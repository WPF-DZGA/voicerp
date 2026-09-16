@echo off
rem Re-run setup: adds languages, repairs a half-finished install, retries
rem downloads that failed. Safe to run any number of times.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0installer\bootstrap.ps1" -AppDir "%~dp0." %*
