@echo off
chcp 65001 > nul
echo ====================================
echo   校园网认证助手 v2.0 - 打包到Release
echo ====================================
echo.

:: 检查PyInstaller
python -c "import PyInstaller" > nul 2>&1
if errorlevel 1 (
    echo [1/4] 安装PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo [1/4] PyInstaller检查通过
echo.

:: 清理旧文件
echo [2/4] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo 清理完成
echo.

:: 开始打包
echo [3/4] 开始打包到release文件夹...
echo 这可能需要几分钟，请耐心等待...
echo.

python -m PyInstaller --distpath="..\release" --workpath="build" build_to_release.spec

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: 清理临时文件
echo.
echo [4/4] 清理临时文件...
if exist "build" rmdir /s /q "build"
echo.

echo ====================================
echo   打包完成！
echo ====================================
echo.
echo 可执行文件位置: ..\release\校园网认证助手_v2.0.exe
echo.
pause
