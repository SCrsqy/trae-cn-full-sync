#!/usr/bin/env python3
"""
数据分析与预测平台 - 项目结构总结
"""
import os

def print_project_structure():
    """打印项目结构"""
    structure = {
        "数据分析与预测平台/": {
            "核心模块": [
                "main.py                    # 主入口",
                "app.py                     # Flask后端服务",
                "business_rules.py          # 核心业务规则",
                "lunar_zodiac.py            # 农历生肖计算",
                "report_generator.py        # Excel报告生成器",
            ],
            "数据层": [
                "data_sources.py            # 数据源配置",
                "anti_crawler.py            # 反爬虫模块",
                "redis_cache.py             # Redis缓存管理",
                "lottery.db                 # SQLite数据库",
            ],
            "调度层": [
                "airflow_dags.py            # Airflow DAG配置",
                "docker-compose.yml         # Docker部署配置",
            ],
            "工具模块": [
                "time_weighted_analyzer.py  # 时间加权分析",
                "event_driven_accuracy.py   # 事件驱动准确率",
            ],
            "输出文件": [
                "统计分析预测报告.xlsx       # 生成的Excel报告",
                "lottery_platform.log       # 系统日志",
            ],
            "配置文件": [
                "requirements.txt           # Python依赖",
                "requirements_optimized.txt # 优化后依赖",
                "schema_audit.sql          # 数据库表结构",
                "start.sh                  # 一键启动脚本",
            ]
        }
    }

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                    数据分析与预测平台 - 项目结构                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    for root, sections in structure.items():
        print(f"📂 {root}")
        for section, files in sections.items():
            print(f"  ├─ 📁 {section}")
            for file in files:
                print(f"  │   └── {file}")
        print()

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                          技术栈说明                                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("""
┌─────────────┬─────────────────────────────────────────────┐
│    层次     │                    技术                      │
├─────────────┼─────────────────────────────────────────────┤
│    前端     │ Vue3 + Element Plus + ECharts + WebSocket    │
│    后端     │ Flask 2.0 / FastAPI                         │
│  任务调度   │ Apache Airflow 2.5+                         │
│    数据库   │ PostgreSQL 14+ / SQLite (开发)               │
│    缓存     │ Redis 6+                                    │
│    爬虫     │ Selenium + requests + BeautifulSoup          │
│  数据分析   │ Pandas + NumPy (仅基础统计)                  │
│    部署     │ Docker Compose / Ubuntu 20.04                │
└─────────────┴─────────────────────────────────────────────┘
""")

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                          数据源配置                               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("""
┌──────┬──────┬─────────────────────────────────────────────────────────┐
│ 地区 │ 代码 │                           URL                           │
├──────┼──────┼─────────────────────────────────────────────────────────┤
│ 澳门 │  AM  │ https://2026kj.zkclhb.com:2025/am.html#toubu13        │
│ 香港 │  HK  │ https://2026kj.zkclhb.com:2025/hk.html#toubu13        │
└──────┴──────┴─────────────────────────────────────────────────────────┘
""")

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                          API接口列表                               ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("""
┌──────────────────────────────────────────────────────────────────────┐
│  GET  /api/predictions/<source>      # 获取预测数据                 │
│  GET  /api/lottery_data/<source>     # 获取开奖数据                 │
│  GET  /api/statistics/<source>       # 获取统计数据                 │
│  GET  /api/sources                   # 获取数据源列表               │
│  POST /api/generate_prediction       # 生成预测                     │
│  POST /api/update_accuracy           # 更新准确率                   │
│  GET  /api/export_report             # 导出报告                     │
│  GET  /health                        # 健康检查                     │
└──────────────────────────────────────────────────────────────────────┘
""")

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                        Airflow调度任务                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("""
┌──────────────────────────────────────────────────────────────────────┐
│  lottery_prediction_pipeline      # 每日22:00 主流程              │
│    ├─ crawl_lottery_data          # 爬虫触发                      │
│    ├─ clean_lottery_data          # 数据清洗                      │
│    ├─ run_statistical_analysis    # 统计分析                      │
│    ├─ generate_predictions        # 预测生成                      │
│    ├─ calculate_accuracy          # 准确率计算                    │
│    └─ export_excel_report         # Excel导出                     │
│                                                                   │
│  daily_prediction_update          # 每日07:00 预测更新            │
│  daily_excel_export               # 每日10:00 Excel导出          │
└──────────────────────────────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    print_project_structure()