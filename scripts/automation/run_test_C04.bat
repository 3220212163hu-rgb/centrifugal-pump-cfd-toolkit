@echo off
chcp 65001 >nul
REM End-to-end single case test - C04_Z5_Beta30

setlocal
set ANSYS_ROOT=D:\ANSYS2024\ANSYS Inc\v242
set WB="%ANSYS_ROOT%\Framework\bin\Win64\RunWB2.exe"
set TG="%ANSYS_ROOT%\TurboGrid\bin\cfxtg.exe"
set SCRIPT_DIR=D:\AI\SJK\biyesheji\scripts\automation

echo ============================================
echo [1/3] BladeGen: load .bgd and pass to TurboGrid
echo ============================================
%WB% -B -R "%SCRIPT_DIR%\01_bladegen_export.wbjn"
if errorlevel 1 (echo BladeGen step FAILED & exit /b 1)

echo ============================================
echo [2/3] TurboGrid: generate mesh
echo ============================================
%TG% -batch "%SCRIPT_DIR%\02_turbogrid.tse"
if errorlevel 1 (echo TurboGrid step FAILED & exit /b 1)

echo ============================================
echo [3/3] Fluent: RANS solve + extract H/eta
echo ============================================
python "%SCRIPT_DIR%\03_fluent_solve.py"
if errorlevel 1 (echo Fluent step FAILED & exit /b 1)

echo.
echo ============================================
echo DONE! Result: D:\AI\SJK\biyesheji\03-vfvjjg\test_C04\result.csv
echo ============================================
endlocal
