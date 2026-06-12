"""
实时报告更新启动器
定期更新Excel报告文件
"""
import sys
import time
import signal
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from report_generator import RealtimeReportUpdater

# 配置
DB_PATH = '/Users/rs/AI/分析预测推荐/lottery.db'
OUTPUT_PATH = '/Users/rs/AI/分析预测推荐/统计分析预测报告.xlsx'
UPDATE_INTERVAL = 60  # 每60秒更新一次

updater = None


def signal_handler(signum, frame):
    """处理退出信号"""
    print("\n收到退出信号，正在停止...")
    if updater:
        updater.stop()
    sys.exit(0)


def main():
    """主函数"""
    global updater

    print("=" * 60)
    print("统计分析预测报告 - 实时更新服务")
    print("=" * 60)
    print(f"数据库: {DB_PATH}")
    print(f"输出文件: {OUTPUT_PATH}")
    print(f"更新间隔: {UPDATE_INTERVAL}秒")
    print("=" * 60)

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建更新器
    updater = RealtimeReportUpdater(DB_PATH, OUTPUT_PATH, UPDATE_INTERVAL)

    print("\n按 Ctrl+C 停止服务\n")

    # 启动更新
    try:
        updater.start()
    except KeyboardInterrupt:
        updater.stop()
        print("服务已停止")


if __name__ == "__main__":
    main()