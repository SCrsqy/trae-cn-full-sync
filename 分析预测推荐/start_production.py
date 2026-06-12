"""
生产环境启动脚本
使用 Gunicorn + gevent 作为 WSGI 服务器
"""
import subprocess
import sys
import os

def start_production_server():
    """启动生产环境服务器"""
    # 检查是否安装了gunicorn
    try:
        import gunicorn
    except ImportError:
        print("安装生产环境依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gunicorn", "gevent"])

    # 启动命令（使用python -m方式，避免PATH问题）
    cmd = [
        sys.executable, "-m", "gunicorn",
        "--workers", "4",                    # 工作进程数
        "--worker-class", "gevent",          # 使用gevent异步
        "--bind", "0.0.0.0:9090",           # 绑定地址和端口
        "--timeout", "120",                  # 超时时间
        "--graceful-timeout", "30",          # 优雅重启超时
        "--access-logfile", "-",             # 访问日志输出到stdout
        "--error-logfile", "-",              # 错误日志输出到stderr
        "--log-level", "info",               # 日志级别
        "prometheus_metrics:create_metrics_app()"  # WSGI应用
    ]

    print(f"启动生产服务器: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    start_production_server()