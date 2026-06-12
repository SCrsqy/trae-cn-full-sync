"""
SQLite版本数据库迁移脚本
无需PostgreSQL，直接运行即可创建数据库表
"""
import sqlite3
import os

DATABASE_PATH = '/Users/rs/AI/分析预测推荐/lottery.db'

# 数据库初始化SQL
SCHEMA_SQL = """
-- 开奖数据表(AM)
CREATE TABLE IF NOT EXISTS lottery_data_am (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_number TEXT NOT NULL UNIQUE,
    draw_date TEXT NOT NULL,
    draw_date_lunar TEXT,
    lunar_year INTEGER,
    lunar_zodiac_year TEXT,
    is_first_after_chunjie INTEGER DEFAULT 0,
    numbers TEXT NOT NULL,
    zodiacs TEXT NOT NULL,
    single_count INTEGER,
    double_count INTEGER,
    big_count INTEGER,
    small_count INTEGER,
    interval_distribution TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 开奖数据表(HK)
CREATE TABLE IF NOT EXISTS lottery_data_hk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_number TEXT NOT NULL UNIQUE,
    draw_date TEXT NOT NULL,
    draw_date_lunar TEXT,
    lunar_year INTEGER,
    lunar_zodiac_year TEXT,
    is_first_after_chunjie INTEGER DEFAULT 0,
    numbers TEXT NOT NULL,
    zodiacs TEXT NOT NULL,
    single_count INTEGER,
    double_count INTEGER,
    big_count INTEGER,
    small_count INTEGER,
    interval_distribution TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 预测记录表(AM)
CREATE TABLE IF NOT EXISTS predictions_am (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_number TEXT NOT NULL UNIQUE,
    predict_date TEXT NOT NULL,
    top6_zodiacs TEXT,
    triple4_groups TEXT,
    top12_numbers TEXT,
    actual_result TEXT,
    hit_rate_top6 REAL,
    hit_rate_triple4 REAL,
    hit_rate_top12 REAL,
    accuracy_rate REAL,
    hit_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 预测记录表(HK)
CREATE TABLE IF NOT EXISTS predictions_hk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_number TEXT NOT NULL UNIQUE,
    predict_date TEXT NOT NULL,
    top6_zodiacs TEXT,
    triple4_groups TEXT,
    top12_numbers TEXT,
    actual_result TEXT,
    hit_rate_top6 REAL,
    hit_rate_triple4 REAL,
    hit_rate_top12 REAL,
    accuracy_rate REAL,
    hit_status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS lottery_data_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    issue_number TEXT NOT NULL,
    operation TEXT NOT NULL,
    data_snapshot TEXT NOT NULL,
    change_reason TEXT,
    source_verified INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system'
);

-- 多源校验记录表
CREATE TABLE IF NOT EXISTS source_verification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    issue_number TEXT NOT NULL,
    source_name TEXT NOT NULL,
    raw_data TEXT NOT NULL,
    fetch_status TEXT NOT NULL,
    error_message TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, issue_number, source_name)
);

-- 准确率统计汇总表
CREATE TABLE IF NOT EXISTS accuracy_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    avg_accuracy_7d REAL,
    avg_accuracy_30d REAL,
    best_issue TEXT,
    worst_issue TEXT,
    details TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_am_issue ON lottery_data_am(issue_number);
CREATE INDEX IF NOT EXISTS idx_hk_issue ON lottery_data_hk(issue_number);
CREATE INDEX IF NOT EXISTS idx_audit_issue ON lottery_data_audit(source_id, issue_number);
"""


def init_database():
    """初始化SQLite数据库"""
    # 删除旧数据库
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"删除旧数据库: {DATABASE_PATH}")

    # 创建新数据库
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"成功创建数据库: {DATABASE_PATH}")

        # 验证表创建
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n创建的表:")
        for table in tables:
            print(f"  - {table[0]}")

    finally:
        conn.close()


def insert_sample_data():
    """插入示例数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # 插入示例开奖数据
        sample_data = {
            'issue_number': '163期',
            'draw_date': '2026-06-12',
            'draw_date_lunar': '甲辰年五月初七',
            'lunar_year': 2024,
            'lunar_zodiac_year': '龙',
            'is_first_after_chunjie': 1,
            'numbers': '[31, 15, 28, 2, 34, 47, 19]',
            'zodiacs': '["鼠", "龙", "兔", "蛇", "鸡", "猴", "鼠"]',
            'single_count': 4,
            'double_count': 3,
            'big_count': 3,
            'small_count': 4,
            'interval_distribution': '{"1-12": 2, "13-24": 2, "25-36": 2, "37-49": 1}'
        }

        cursor.execute("""
            INSERT INTO lottery_data_am 
            (issue_number, draw_date, draw_date_lunar, lunar_year, lunar_zodiac_year,
             is_first_after_chunjie, numbers, zodiacs, single_count, double_count,
             big_count, small_count, interval_distribution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sample_data['issue_number'],
            sample_data['draw_date'],
            sample_data['draw_date_lunar'],
            sample_data['lunar_year'],
            sample_data['lunar_zodiac_year'],
            sample_data['is_first_after_chunjie'],
            sample_data['numbers'],
            sample_data['zodiacs'],
            sample_data['single_count'],
            sample_data['double_count'],
            sample_data['big_count'],
            sample_data['small_count'],
            sample_data['interval_distribution']
        ))

        conn.commit()
        print("\n成功插入示例数据")

    finally:
        conn.close()


def verify_database():
    """验证数据库状态"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # 检查表记录数
        print("\n数据库验证:")

        cursor.execute("SELECT COUNT(*) FROM lottery_data_am")
        count = cursor.fetchone()[0]
        print(f"  lottery_data_am: {count} 条记录")

        cursor.execute("SELECT COUNT(*) FROM predictions_am")
        count = cursor.fetchone()[0]
        print(f"  predictions_am: {count} 条记录")

        cursor.execute("SELECT COUNT(*) FROM lottery_data_audit")
        count = cursor.fetchone()[0]
        print(f"  lottery_data_audit: {count} 条记录")

        # 查询示例数据
        cursor.execute("SELECT * FROM lottery_data_am WHERE issue_number = '163期'")
        row = cursor.fetchone()
        if row:
            print(f"\n  示例数据:")
            print(f"    期号: {row[1]}")
            print(f"    日期: {row[2]}")
            print(f"    生肖年: {row[5]}")
            print(f"    号码: {row[7]}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("SQLite数据库初始化")
    print("=" * 60)

    init_database()
    insert_sample_data()
    verify_database()

    print("\n" + "=" * 60)
    print("数据库初始化完成!")
    print("=" * 60)