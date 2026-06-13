#!/bin/bash
# ==============================================================================
# 数据分析与预测平台 - 一键启动脚本
# ==============================================================================

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    数据分析与预测平台                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "🔍 检查依赖..."
python3 -c "import openpyxl, flask, flask_socketio" 2>/dev/null || {
    echo "📦 安装依赖..."
    pip3 install openpyxl flask flask-socketio flask-cors requests beautifulsoup4
}

echo "✅ 依赖检查完成"

# 启动后端服务
echo "🚀 启动后端服务..."
cd "$(dirname "$0")"

# 启动Flask服务
echo "   - 启动Flask API服务..."
python3 app.py &
FLASK_PID=$!
echo "     Flask服务PID: $FLASK_PID"

# 等待服务启动
sleep 3

# 检查服务状态
if curl -s http://localhost:5000/health > /dev/null; then
    echo "✅ Flask服务启动成功"
else
    echo "❌ Flask服务启动失败"
    kill $FLASK_PID 2>/dev/null
    exit 1
fi

# 启动主程序
echo "   - 启动主程序..."
python3 main.py &
MAIN_PID=$!
echo "     主程序PID: $MAIN_PID"

echo ""
echo "🎉 服务启动完成！"
echo "──────────────────────────────────────────────────────────────────────"
echo "API地址: http://localhost:5000"
echo "WebSocket: ws://localhost:5000/socket.io"
echo "报告文件: 统计分析预测报告.xlsx"
echo "──────────────────────────────────────────────────────────────────────"
echo "按 Ctrl+C 停止服务"

# 等待用户中断
trap 'echo "🛑 正在停止服务..."; kill $FLASK_PID $MAIN_PID 2>/dev/null; exit 0' INT

wait