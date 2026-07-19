@echo off
title Installing CapCut Timeline Sync Tool Dependencies
echo ==================================================
echo.
echo DANG CAI DAT CAC THU VIEN PYTHON CAN THIET...
echo.
echo ==================================================
python -m pip install --upgrade pip
python -m pip install pyJianYingDraft

echo.
echo ==================================================
echo.
echo DANG KIEM TRA VA TAI VE FILE FFPROBE.EXE PORTABLE...
echo.
echo ==================================================
if exist "%~dp0ffprobe.exe" (
    echo [INFO] ffprobe.exe da ton tai san.
) else (
    echo [INFO] Dang tai ffprobe.exe...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip' -OutFile '%~dp0ffprobe.zip'"
    if exist "%~dp0ffprobe.zip" (
        echo [INFO] Dang giai nen file ffprobe.zip...
        powershell -Command "Expand-Archive -Path '%~dp0ffprobe.zip' -DestinationPath '%~dp0' -Force"
        del "%~dp0ffprobe.zip"
        echo [OK] Tải va giai nen ffprobe.exe thanh cong!
    ) else (
        echo [ERROR] Khong the tai xuong ffprobe.exe. Vui long kiem tra ket noi mang.
    )
)

echo.
echo ==================================================
echo Hoan tat cai dat! Ban co the chay ung dung bang file run.bat.
echo ==================================================
pause
