@echo off
title CapCut Timeline Sync Tool
echo Dang khoi dong CapCut Timeline Sync Tool...
python "%~dp0gui_app.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Co loi xay ra khi chay chuong trinh.
    pause
)
