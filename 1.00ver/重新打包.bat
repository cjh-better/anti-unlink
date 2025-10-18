@echo off
chcp 65001 >nul
echo ============================================
echo 校园网认证工具 - 重新打包
echo ============================================
echo.

cd /d "%~dp0"

echo [1] 清理旧文件...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "*.spec" del /q "*.spec"
if exist "..\release\校园网认证工具.exe" del /q "..\release\校园网认证工具.exe"
echo     ✓ 清理完成
echo.

echo [2] 开始打包...
pyinstaller --onefile --noconsole --name="校园网认证工具" --icon=image.ico --add-data="image.ico;." --add-data="wifi_icon.png;." --add-data="stop_icon.png;." --add-data="start_icon.png;." --add-data="user_icon.png;." --add-data="password_icon.png;." --add-data="eyes_icon.png;." --add-data="eyes_closed_icon.png;." --hidden-import=maliang --hidden-import=PIL --hidden-import=PIL._tkinter_finder gui.py

if errorlevel 1 (
    echo     ✗ 打包失败！
    pause
    exit /b 1
)

echo     ✓ 打包完成
echo.

echo [3] 移动到release目录...
if not exist "..\release" mkdir "..\release"
move /y "dist\校园网认证工具.exe" "..\release\校园网认证工具.exe" >nul
if errorlevel 1 (
    echo     ✗ 移动失败！
    pause
    exit /b 1
)
echo     ✓ 已保存到release
echo.

echo [4] 清理临时文件...
rd /s /q "build"
rd /s /q "dist"
del /q "*.spec"
echo     ✓ 清理完成
echo.

echo ============================================
echo 打包完成
echo ============================================
pause
