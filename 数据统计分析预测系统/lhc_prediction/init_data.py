#!/usr/bin/env python3
"""初始化数据库并插入模拟数据"""

import sqlite3
import random
from datetime import datetime, timedelta
from config import DATABASE_PATH, ZODIAC_MAP

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS draw_results')
    
    cursor.execute('''
        CREATE TABLE draw_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            issue TEXT NOT NULL,
            draw_date TEXT NOT NULL,
            numbers TEXT NOT NULL,
            special_number INTEGER NOT NULL,
            special_zodiac TEXT,
            UNIQUE(region, issue)
        )
    ''')
    
    conn.commit()
    conn.close()
    print('数据库表已创建')

def generate_draw_numbers():
    all_numbers = list(range(1, 50))
    random.shuffle(all_numbers)
    main_numbers = sorted(all_numbers[:6])
    special_number = all_numbers[6]
    return main_numbers, special_number

def get_zodiac(number):
    for zodiac, numbers in ZODIAC_MAP.items():
        if number in numbers:
            return zodiac
    return None

def insert_mock_data():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    today = datetime.now()
    
    print('=== 插入澳门数据 (第1期 ~ 第163期) ===')
    for issue_num in range(1, 164):
        issue = str(issue_num).zfill(3)
        days_ago = (163 - issue_num) * 7 + random.randint(-1, 1)
        draw_date = (today - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        main_numbers, special_number = generate_draw_numbers()
        special_zodiac = get_zodiac(special_number)
        
        cursor.execute('''
            INSERT INTO draw_results (region, issue, draw_date, numbers, special_number, special_zodiac)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('am', issue, draw_date, ','.join(map(str, main_numbers)), special_number, special_zodiac))
        
        if issue_num % 50 == 0:
            print(f'已插入澳门第{issue_num}期...')
    
    print('=== 插入香港数据 (第1期 ~ 第63期) ===')
    for issue_num in range(1, 64):
        issue = str(issue_num).zfill(3)
        days_ago = (63 - issue_num) * 7 + random.randint(-1, 1)
        draw_date = (today - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        main_numbers, special_number = generate_draw_numbers()
        special_zodiac = get_zodiac(special_number)
        
        cursor.execute('''
            INSERT INTO draw_results (region, issue, draw_date, numbers, special_number, special_zodiac)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('hk', issue, draw_date, ','.join(map(str, main_numbers)), special_number, special_zodiac))
        
        if issue_num % 20 == 0:
            print(f'已插入香港第{issue_num}期...')
    
    conn.commit()
    conn.close()
    print('数据插入完成')

def verify_data():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT MIN(issue), MAX(issue), COUNT(*) FROM draw_results WHERE region = ?', ('am',))
    am_stats = cursor.fetchone()
    print(f'\n澳门数据: 第{int(am_stats[0])}期 ~ 第{int(am_stats[1])}期, 共{am_stats[2]}期')
    
    cursor.execute('SELECT MIN(issue), MAX(issue), COUNT(*) FROM draw_results WHERE region = ?', ('hk',))
    hk_stats = cursor.fetchone()
    print(f'香港数据: 第{int(hk_stats[0])}期 ~ 第{int(hk_stats[1])}期, 共{hk_stats[2]}期')
    
    cursor.execute('SELECT issue, draw_date, special_number, special_zodiac FROM draw_results WHERE region = ? ORDER BY issue DESC LIMIT 1', ('am',))
    last_am = cursor.fetchone()
    print(f'\n澳门最新: 第{int(last_am[0])}期, 日期:{last_am[1]}, 特码:{last_am[2]}, 生肖:{last_am[3]}')
    
    cursor.execute('SELECT issue, draw_date, special_number, special_zodiac FROM draw_results WHERE region = ? ORDER BY issue DESC LIMIT 1', ('hk',))
    last_hk = cursor.fetchone()
    print(f'香港最新: 第{int(last_hk[0])}期, 日期:{last_hk[1]}, 特码:{last_hk[2]}, 生肖:{last_hk[3]}')
    
    conn.close()

if __name__ == '__main__':
    init_database()
    insert_mock_data()
    verify_data()