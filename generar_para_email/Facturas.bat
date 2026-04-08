@echo off
cd /d "%~dp0"
uv run main.py
if errorlevel 1 pause
