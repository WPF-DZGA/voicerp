@echo off
rem VoiceRP. pythonw.exe = no console window.
cd /d "%~dp0translate"
if not exist "%~dp0venv\Scripts\pythonw.exe" (
  echo VoiceRP is not set up yet. Run "VoiceRP setup / repair" from the Start menu.
  pause
  exit /b 1
)
start "" "%~dp0venv\Scripts\pythonw.exe" gui.py
