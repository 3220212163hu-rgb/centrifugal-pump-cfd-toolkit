@echo off
chcp 65001 >nul
D:
cd \AI\SJK\biyesheji\scripts\automation
"D:\ANSYS2024\ANSYS Inc\v242\Framework\bin\Win64\RunWB2.exe" -B -R "D:\AI\SJK\biyesheji\scripts\automation\01_bladegen_export.wbjn"
echo EXIT=%errorlevel%
