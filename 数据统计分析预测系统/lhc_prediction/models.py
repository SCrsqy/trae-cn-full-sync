import sqlite3
import os
from config import DATABASE_PATH

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS draw_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            issue TEXT NOT NULL,
            draw_date TEXT NOT NULL,
            numbers TEXT NOT NULL,
            special_number INTEGER NOT NULL,
            zodiac TEXT,
            UNIQUE(region, issue)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            issue TEXT NOT NULL,
            pred_type TEXT NOT NULL,
            content TEXT NOT NULL,
            actual_special INTEGER,
            is_correct INTEGER DEFAULT 0,
            accuracy REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            issue TEXT NOT NULL,
            bet_amount REAL NOT NULL,
            odds REAL NOT NULL,
            pred_numbers TEXT NOT NULL,
            actual_special INTEGER,
            is_won INTEGER DEFAULT 0,
            investment REAL DEFAULT 0.0,
            return_amount REAL DEFAULT 0.0,
            net_profit REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period VARCHAR(20) NOT NULL,
            draw_date DATE NOT NULL,
            nums VARCHAR(50) NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('AM', 'HK')),
            UNIQUE(period)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stat_num_freq (
            num INTEGER PRIMARY KEY,
            zodiac VARCHAR(5) NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            freq DECIMAL(5,2) NOT NULL DEFAULT 0.00
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stat_zodiac_freq (
            zodiac VARCHAR(5) PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0,
            freq DECIMAL(5,2) NOT NULL DEFAULT 0.00
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stat_three_zodiac (
            z1 VARCHAR(5),
            z2 VARCHAR(5),
            z3 VARCHAR(5),
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (z1, z2, z3)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prediction_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period VARCHAR(20) NOT NULL UNIQUE,
            six_zodiac TEXT NOT NULL,
            three_group TEXT NOT NULL,
            hot_12_num TEXT NOT NULL,
            acc_six REAL DEFAULT NULL,
            acc_three REAL DEFAULT NULL,
            acc_hot12 REAL DEFAULT NULL,
            acc_weight REAL DEFAULT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

def get_next_issue(region):
    """获取下期期号"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT issue FROM draw_results WHERE region = ? ORDER BY issue DESC LIMIT 1', (region,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        last_issue = result[0]
        if len(last_issue) >= 7:
            year = int(last_issue[:4])
            num = int(last_issue[4:])
            return f'{year}{num + 1:03d}'
    return '2026001'

def get_last_draw(region):
    """获取最近一期开奖记录"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM draw_results WHERE region = ? ORDER BY issue DESC LIMIT 1', (region,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'region': result[1],
            'issue': result[2],
            'draw_date': result[3],
            'numbers': result[4],
            'special_number': result[5],
            'zodiac': result[6]
        }
    return None

def save_to_lottery_history(period, draw_date, nums, source):
    """保存数据到lottery_history表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO lottery_history (period, draw_date, nums, source)
            VALUES (?, ?, ?, ?)
        ''', (period, draw_date, nums, source))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f'保存到lottery_history失败: {e}')
        return False
    finally:
        conn.close()

def get_lottery_history(source=None):
    """获取lottery_history数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        if source:
            cursor.execute('SELECT * FROM lottery_history WHERE source = ? ORDER BY period DESC', (source,))
        else:
            cursor.execute('SELECT * FROM lottery_history ORDER BY period DESC')
        results = cursor.fetchall()
        return [{
            'id': row[0],
            'period': row[1],
            'draw_date': row[2],
            'nums': row[3],
            'source': row[4]
        } for row in results]
    except Exception as e:
        print(f'获取lottery_history失败: {e}')
        return []
    finally:
        conn.close()

def get_lottery_by_period(period):
    """根据期号获取记录"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM lottery_history WHERE period = ?', (period,))
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'period': result[1],
                'draw_date': result[2],
                'nums': result[3],
                'source': result[4]
            }
        return None
    except Exception as e:
        print(f'获取lottery_history失败: {e}')
        return None
    finally:
        conn.close()

def save_stat_num_freq(num, zodiac, count, freq):
    """保存数字频率数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO stat_num_freq (num, zodiac, count, freq)
            VALUES (?, ?, ?, ?)
        ''', (num, zodiac, count, freq))
        conn.commit()
        return True
    except Exception as e:
        print(f'保存数字频率失败: {e}')
        return False
    finally:
        conn.close()

def save_stat_zodiac_freq(zodiac, count, freq):
    """保存生肖频率数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO stat_zodiac_freq (zodiac, count, freq)
            VALUES (?, ?, ?)
        ''', (zodiac, count, freq))
        conn.commit()
        return True
    except Exception as e:
        print(f'保存生肖频率失败: {e}')
        return False
    finally:
        conn.close()

def save_stat_three_zodiac(z1, z2, z3, count):
    """保存三肖组合数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO stat_three_zodiac (z1, z2, z3, count)
            VALUES (?, ?, ?, ?)
        ''', (z1, z2, z3, count))
        conn.commit()
        return True
    except Exception as e:
        print(f'保存三肖组合失败: {e}')
        return False
    finally:
        conn.close()

def get_stat_num_freq(top_n=None):
    """获取数字频率数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        if top_n:
            cursor.execute('SELECT * FROM stat_num_freq ORDER BY count DESC LIMIT ?', (top_n,))
        else:
            cursor.execute('SELECT * FROM stat_num_freq ORDER BY num')
        results = cursor.fetchall()
        return [{
            'num': row[0],
            'zodiac': row[1],
            'count': row[2],
            'freq': row[3]
        } for row in results]
    except Exception as e:
        print(f'获取数字频率失败: {e}')
        return []
    finally:
        conn.close()

def get_stat_zodiac_freq():
    """获取生肖频率数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM stat_zodiac_freq ORDER BY count DESC')
        results = cursor.fetchall()
        return [{
            'zodiac': row[0],
            'count': row[1],
            'freq': row[2]
        } for row in results]
    except Exception as e:
        print(f'获取生肖频率失败: {e}')
        return []
    finally:
        conn.close()

def get_stat_three_zodiac(top_n=None):
    """获取三肖组合数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        if top_n:
            cursor.execute('SELECT * FROM stat_three_zodiac ORDER BY count DESC LIMIT ?', (top_n,))
        else:
            cursor.execute('SELECT * FROM stat_three_zodiac ORDER BY count DESC')
        results = cursor.fetchall()
        return [{
            'z1': row[0],
            'z2': row[1],
            'z3': row[2],
            'count': row[3]
        } for row in results]
    except Exception as e:
        print(f'获取三肖组合失败: {e}')
        return []
    finally:
        conn.close()

def clear_stat_tables():
    """清空统计表数据"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM stat_num_freq')
        cursor.execute('DELETE FROM stat_zodiac_freq')
        cursor.execute('DELETE FROM stat_three_zodiac')
        conn.commit()
        return True
    except Exception as e:
        print(f'清空统计表失败: {e}')
        return False
    finally:
        conn.close()

def save_prediction_record(period, six_zodiac, three_group, hot_12_num, acc_six=None, acc_three=None, acc_hot12=None, acc_weight=None):
    """保存预测记录"""
    import json
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        six_zodiac_json = json.dumps(six_zodiac, ensure_ascii=False) if isinstance(six_zodiac, (list, dict)) else six_zodiac
        three_group_json = json.dumps(three_group, ensure_ascii=False) if isinstance(three_group, (list, dict)) else three_group
        hot_12_num_json = json.dumps(hot_12_num, ensure_ascii=False) if isinstance(hot_12_num, (list, dict)) else hot_12_num
        
        cursor.execute('''
            INSERT OR REPLACE INTO prediction_record 
            (period, six_zodiac, three_group, hot_12_num, acc_six, acc_three, acc_hot12, acc_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (period, six_zodiac_json, three_group_json, hot_12_num_json, acc_six, acc_three, acc_hot12, acc_weight))
        conn.commit()
        return True
    except Exception as e:
        print(f'保存预测记录失败: {e}')
        return False
    finally:
        conn.close()

def get_prediction_record(period):
    """根据期号获取预测记录"""
    import json
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM prediction_record WHERE period = ?', (period,))
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'period': result[1],
                'six_zodiac': json.loads(result[2]) if result[2] else None,
                'three_group': json.loads(result[3]) if result[3] else None,
                'hot_12_num': json.loads(result[4]) if result[4] else None,
                'acc_six': result[5],
                'acc_three': result[6],
                'acc_hot12': result[7],
                'acc_weight': result[8],
                'create_time': result[9],
                'update_time': result[10]
            }
        return None
    except Exception as e:
        print(f'获取预测记录失败: {e}')
        return None
    finally:
        conn.close()

def get_all_prediction_records(limit=None):
    """获取所有预测记录"""
    import json
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        if limit:
            cursor.execute('SELECT * FROM prediction_record ORDER BY create_time DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM prediction_record ORDER BY create_time DESC')
        results = cursor.fetchall()
        return [{
            'id': row[0],
            'period': row[1],
            'six_zodiac': json.loads(row[2]) if row[2] else None,
            'three_group': json.loads(row[3]) if row[3] else None,
            'hot_12_num': json.loads(row[4]) if row[4] else None,
            'acc_six': row[5],
            'acc_three': row[6],
            'acc_hot12': row[7],
            'acc_weight': row[8],
            'create_time': row[9],
            'update_time': row[10]
        } for row in results]
    except Exception as e:
        print(f'获取预测记录列表失败: {e}')
        return []
    finally:
        conn.close()

def update_prediction_accuracy(period, acc_six=None, acc_three=None, acc_hot12=None, acc_weight=None):
    """更新预测准确率"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        updates = []
        values = []
        if acc_six is not None:
            updates.append('acc_six = ?')
            values.append(acc_six)
        if acc_three is not None:
            updates.append('acc_three = ?')
            values.append(acc_three)
        if acc_hot12 is not None:
            updates.append('acc_hot12 = ?')
            values.append(acc_hot12)
        if acc_weight is not None:
            updates.append('acc_weight = ?')
            values.append(acc_weight)
        
        if updates:
            updates.append('update_time = CURRENT_TIMESTAMP')
            values.append(period)
            sql = f"UPDATE prediction_record SET {', '.join(updates)} WHERE period = ?"
            cursor.execute(sql, values)
            conn.commit()
        return True
    except Exception as e:
        print(f'更新预测准确率失败: {e}')
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
    print('数据库初始化完成')