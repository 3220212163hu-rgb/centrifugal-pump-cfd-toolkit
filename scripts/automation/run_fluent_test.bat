@echo off
chcp 65001 >nul
D:
cd \AI\SJK\biyesheji\scripts\automation
D:\AI\SJK\biyesheji\venv_pyfluent_win\Scripts\python.exe test_fluent_only.py
echo EXIT=%errorlevel%
pause
