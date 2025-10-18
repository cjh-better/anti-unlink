@echo off
chcp 65001 > nul
echo ====================================
echo   校园网认证助手 v2.0 - 启动器
echo ====================================
echo.

:: 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Python环境检查通过
echo.

:: 检查依赖是否安装
python -c "import PySide6" > nul 2>&1
if errorlevel 1 (
    echo [2/3] 首次运行，正在安装依赖...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo 依赖安装完成!
) else (
    echo [2/3] 依赖检查通过
)
echo.

:: 启动程序
echo [3/3] 启动程序中...
echo.
python main_campus.py

if errorlevel 1 (
    echo.
    echo [错误] 程序启动失败，请查看错误信息
    pause
)
