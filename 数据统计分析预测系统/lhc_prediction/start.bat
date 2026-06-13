@echo off

echo 正在检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo 正在创建虚拟环境...
python -m venv venv

echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo 正在安装依赖...
pip install -r requirements.txt

echo 启动 Flask 服务...
python app.py

pause