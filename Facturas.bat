@echo off
cd /d "%~dp0generar_para_email"
uv run main.py
if errorlevel 1 pause
