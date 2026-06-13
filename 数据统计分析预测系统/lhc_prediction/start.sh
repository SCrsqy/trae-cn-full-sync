#!/bin/bash

echo "正在检查 Python3..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

echo "正在创建虚拟环境..."
python3 -m venv venv

echo "正在激活虚拟环境..."
source venv/bin/activate

echo "正在安装依赖..."
pip install -r requirements.txt

echo "启动 Flask 服务..."
python app.py