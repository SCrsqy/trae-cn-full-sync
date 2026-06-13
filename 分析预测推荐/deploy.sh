#!/bin/bash
# ==============================================================================
# 数据分析与预测平台 - Ubuntu 20.04 部署脚本
# ==============================================================================

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              数据分析与预测平台 - 部署脚本                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# 1. 系统更新
echo ""
echo "📦 步骤1: 系统更新..."
sudo apt update && sudo apt upgrade -y

# 2. 安装基础依赖
echo ""
echo "📦 步骤2: 安装基础依赖..."
sudo apt install -y python3.9 python3.9-dev python3-pip \
                   postgresql-14 redis-server \
                   chromium-browser chromium-chromedriver \
                   git curl wget

# 3. 设置Python环境
echo ""
echo "📦 步骤3: 设置Python环境..."
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
sudo update-alternatives --set python3 /usr/bin/python3.9

# 4. 安装Python依赖
echo ""
echo "📦 步骤4: 安装Python依赖..."
pip3 install --upgrade pip
pip3 install apache-airflow==2.5.0 pandas selenium flask flask-cors flask-socketio \
             psycopg2-binary openpyxl redis requests beautifulsoup4

# 5. 配置PostgreSQL
echo ""
echo "📦 步骤5: 配置PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE DATABASE lottery;"
sudo -u postgres psql -c "CREATE USER admin WITH PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lottery TO admin;"

# 6. 配置Redis
echo ""
echo "📦 步骤6: 配置Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 7. 创建项目目录
echo ""
echo "📦 步骤7: 创建项目目录..."
mkdir -p /opt/lottery/{logs,backup,data}
mkdir -p /opt/airflow/dags

# 8. 复制项目文件
echo ""
echo "📦 步骤8: 复制项目文件..."
cp -r ./* /opt/lottery/
cp airflow_dags.py /opt/airflow/dags/lottery_dag.py

# 9. 初始化Airflow
echo ""
echo "📦 步骤9: 初始化Airflow..."
export AIRFLOW_HOME=/opt/airflow
airflow db init

# 创建Airflow用户
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# 10. 创建环境变量配置
echo ""
echo "📦 步骤10: 创建环境变量配置..."
cat > /opt/lottery/.env << 'EOF'
# 数据库配置
DB_URL=postgresql://admin:password@localhost/lottery
REDIS_URL=redis://localhost:6379/0

# 数据源配置
AM_URL=https://2026kj.zkclhb.com:2025/am.html#toubu13
HK_URL=https://2026kj.zkclhb.com:2025/hk.html#toubu13

# 生肖映射表路径
ZODIAC_MAPPING_PATH=/opt/lottery/2026年50岁以内生肖对应表.xlsx

# 企业微信告警（可选）
# WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
EOF

# 11. 启动服务
echo ""
echo "📦 步骤11: 启动服务..."

# 启动Airflow
export AIRFLOW_HOME=/opt/airflow
airflow webserver -p 8080 -D
sleep 10
airflow scheduler -D

# 启动Flask API
cd /opt/lottery
nohup python3 app.py > /opt/lottery/logs/flask.log 2>&1 &

echo ""
echo "🎉 部署完成!"
echo ""
echo "服务地址:"
echo "  Airflow: http://localhost:8080"
echo "  Flask API: http://localhost:5000"
echo ""
echo "下一步操作:"
echo "  1. 访问 Airflow 配置DAG"
echo "  2. 执行全量数据爬取"
echo "  3. 配置告警Webhook"