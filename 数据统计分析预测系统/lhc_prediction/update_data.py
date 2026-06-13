#!/usr/bin/env python3
"""数据更新脚本 - 更新六合彩数据并生成报告"""

import sqlite3
import datetime
from config import DATABASE_PATH
from crawler import crawl

def generate_update_report():
    print('=' * 60)
    print('数据更新报告生成')
    print('=' * 60)
    
    update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n更新时间: {update_time}')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取更新前数据
    cursor.execute('SELECT COUNT(*) FROM draw_results WHERE region = ?', ('am',))
    am_before = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(issue) FROM draw_results WHERE region = ?', ('am',))
    am_last_before = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM draw_results WHERE region = ?', ('hk',))
    hk_before = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(issue) FROM draw_results WHERE region = ?', ('hk',))
    hk_last_before = cursor.fetchone()[0]
    
    print('\n【更新前数据状态】')
    print(f'  澳门地区: {am_before}条记录，最新期号: {am_last_before}')
    print(f'  香港地区: {hk_before}条记录，最新期号: {hk_last_before}')
    
    print('\n【开始更新数据...】')
    
    # 执行数据爬取
    am_count = crawl('am', use_mock=True)
    hk_count = crawl('hk', use_mock=True)
    
    # 获取更新后数据
    cursor.execute('SELECT COUNT(*) FROM draw_results WHERE region = ?', ('am',))
    am_after = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(issue) FROM draw_results WHERE region = ?', ('am',))
    am_last_after = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM draw_results WHERE region = ?', ('hk',))
    hk_after = cursor.fetchone()[0]
    cursor.execute('SELECT MAX(issue) FROM draw_results WHERE region = ?', ('hk',))
    hk_last_after = cursor.fetchone()[0]
    
    conn.close()
    
    print('\n【更新后数据状态】')
    print(f'  澳门地区: {am_after}条记录，最新期号: {am_last_after}')
    print(f'  香港地区: {hk_after}条记录，最新期号: {hk_last_after}')
    
    print('\n【更新详情】')
    print(f'  澳门新增记录: {am_after - am_before}条')
    print(f'  香港新增记录: {hk_after - hk_before}条')
    print(f'  总计新增记录: {(am_after - am_before) + (hk_after - hk_before)}条')
    
    if am_last_before != am_last_after:
        print(f'  澳门期号更新: {am_last_before} -> {am_last_after}')
    if hk_last_before != hk_last_after:
        print(f'  香港期号更新: {hk_last_before} -> {hk_last_after}')
    
    print('\n' + '=' * 60)
    print('数据更新完成！')
    print('=' * 60)

if __name__ == '__main__':
    generate_update_report()