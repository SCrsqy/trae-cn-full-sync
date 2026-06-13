#!/usr/bin/env python3
"""
数据分析与预测平台主入口
整合调度层、数据层、业务逻辑层和展示层
"""
import os
import sys
import time
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lottery_platform.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def start_crawler():
    """启动爬虫服务"""
    logger.info("启动爬虫服务...")
    try:
        from data_sources import DataSourceCrawler, DataSourceManager
        from anti_crawler import AdvancedCrawler
        
        manager = DataSourceManager()
        crawler = DataSourceCrawler()
        
        # 抓取所有数据源
        results = crawler.crawl_all_sources()
        
        for source_code, data in results.items():
            source = manager.get_source(source_code)
            logger.info(f"从 {source.name} 抓取到 {len(data)} 条数据")
        
        return True
    except Exception as e:
        logger.error(f"爬虫启动失败: {e}")
        return False


def start_prediction():
    """启动预测服务"""
    logger.info("启动预测服务...")
    try:
        from business_rules import PredictionGenerator
        
        generator = PredictionGenerator('/Users/rs/AI/分析预测推荐/lottery.db')
        
        # 为两个数据源生成预测
        pred_am = generator.generate_prediction('AM')
        pred_hk = generator.generate_prediction('HK')
        
        logger.info(f"生成澳门预测: {pred_am.issue_number}")
        logger.info(f"生成香港预测: {pred_hk.issue_number}")
        
        return True
    except Exception as e:
        logger.error(f"预测服务启动失败: {e}")
        return False


def start_accuracy_calculation():
    """启动准确率计算服务"""
    logger.info("启动准确率计算服务...")
    try:
        from business_rules import AccuracyCalculator
        
        calculator = AccuracyCalculator('/Users/rs/AI/分析预测推荐/lottery.db')
        
        # 批量更新准确率
        updated_am = calculator.batch_update_accuracy('AM')
        updated_hk = calculator.batch_update_accuracy('HK')
        
        logger.info(f"更新澳门准确率: {updated_am} 条")
        logger.info(f"更新香港准确率: {updated_hk} 条")
        
        return True
    except Exception as e:
        logger.error(f"准确率计算启动失败: {e}")
        return False


def start_report_generator():
    """启动报告生成服务"""
    logger.info("启动报告生成服务...")
    try:
        from report_generator import ReportGenerator
        
        generator = ReportGenerator(
            db_path='/Users/rs/AI/分析预测推荐/lottery.db',
            output_path='/Users/rs/AI/分析预测推荐/统计分析预测报告.xlsx',
            sources=['AM', 'HK']
        )
        
        success = generator.generate_report()
        
        if success:
            logger.info("报告生成成功")
        else:
            logger.warning("报告生成失败")
        
        return success
    except Exception as e:
        logger.error(f"报告生成启动失败: {e}")
        return False


def start_real_time_updater():
    """启动实时更新服务"""
    logger.info("启动实时更新服务...")
    try:
        from redis_cache import RedisCache, RealTimeUpdater
        
        cache = RedisCache()
        updater = RealTimeUpdater('/Users/rs/AI/分析预测推荐/lottery.db', cache)
        
        updater.start()
        logger.info("实时更新服务已启动")
        
        return updater
    except Exception as e:
        logger.error(f"实时更新服务启动失败: {e}")
        return None


def print_system_info():
    """打印系统信息"""
    print("=" * 70)
    print("       数据分析与预测平台 - 系统信息")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("模块列表:")
    print("  [1] 数据源配置       - data_sources.py")
    print("  [2] 爬虫模块         - anti_crawler.py")
    print("  [3] 农历生肖计算     - lunar_zodiac.py")
    print("  [4] 业务规则         - business_rules.py")
    print("  [5] 报告生成器       - report_generator.py")
    print("  [6] Redis缓存        - redis_cache.py")
    print("  [7] Airflow调度      - airflow_dags.py")
    print("=" * 70)


def main():
    """主函数"""
    print_system_info()
    
    # 启动各个模块
    modules = [
        ("爬虫服务", start_crawler),
        ("预测服务", start_prediction),
        ("准确率计算", start_accuracy_calculation),
        ("报告生成", start_report_generator),
    ]
    
    results = []
    for name, func in modules:
        try:
            success = func()
            status = "✓" if success else "✗"
            results.append((name, status))
        except Exception as e:
            logger.error(f"{name}启动异常: {e}")
            results.append((name, "✗"))
    
    # 打印启动结果
    print("\n启动结果:")
    for name, status in results:
        print(f"  {status} {name}")
    
    # 启动实时更新服务（后台运行）
    updater = start_real_time_updater()
    
    # 保持运行
    if updater:
        print("\n实时更新服务已启动，按 Ctrl+C 停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            updater.stop()
            print("\n服务已停止")


if __name__ == "__main__":
    main()