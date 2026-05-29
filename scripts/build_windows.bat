@echo off
REM 图片格式转换工具 — Windows 打包

cd /d "%~dp0\.."
set APP_NAME=图片格式转换工具

echo ==========================================
echo %APP_NAME% - Windows 打包
echo ==========================================

where pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 请先安装 PyInstaller
    echo   pip install pyinstaller
    pause
    exit /b 1
)

pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

set ICON_PARAM=
if exist app_icon.ico set ICON_PARAM=--icon=app_icon.ico

pyinstaller --name="%APP_NAME%" ^
    --windowed ^
    --onedir ^
    --clean ^
    --noconfirm ^
    --hidden-import=customtkinter ^
    --hidden-import=PIL ^
    --hidden-import=pillow_heif ^
    --collect-all=pillow_heif ^
    --add-data "shared;shared" ^
    %ICON_PARAM% ^
    image_converter/gui_ctk.py

if exist "dist\%APP_NAME%" (
    echo.
    echo 打包成功: dist\%APP_NAME%\
) else (
    echo 打包失败
    exit /b 1
)

if "%CI%"=="" pause
