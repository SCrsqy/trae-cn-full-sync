import sqlite3
from collections import Counter
from itertools import combinations
from datetime import datetime
from config import DATABASE_PATH, ZODIAC_MAP, ZODIAC_ORDER

PREDICTION_MODEL_VERSION = "v2.1.0"

def get_all_draw_results(region):
    """
    获取该地区从第一期到最近一期的所有开奖结果，按期号升序排列
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    # 按期号升序排列，确保从第一期到最近一期的顺序
    cursor.execute('SELECT numbers, special_number, issue, draw_date FROM draw_results WHERE region = ? ORDER BY issue ASC', (region,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_total_draw_count(region):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM draw_results WHERE region = ?', (region,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_issue_range(region):
    """
    获取该地区的期号范围（第一期和最近一期）
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MIN(issue), MAX(issue) FROM draw_results WHERE region = ?', (region,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'first_issue': result[0], 'last_issue': result[1]}
    return {'first_issue': None, 'last_issue': None}

def calculate_number_frequency(region):
    results = get_all_draw_results(region)
    all_numbers = []
    
    for row in results:
        numbers = [int(n) for n in row[0].split(',')]
        numbers.append(row[1])
        all_numbers.extend(numbers)
    
    frequency = Counter(all_numbers)
    total = sum(frequency.values())
    sorted_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
    return [(num, freq, freq/total*100 if total > 0 else 0) for num, freq in sorted_freq]

def calculate_zodiac_frequency(region):
    results = get_all_draw_results(region)
    zodiac_counts = Counter()
    
    for row in results:
        special_num = row[1]
        for zodiac, numbers in ZODIAC_MAP.items():
            if special_num in numbers:
                zodiac_counts[zodiac] += 1
                break
    
    total = sum(zodiac_counts.values())
    sorted_zodiac = sorted(zodiac_counts.items(), key=lambda x: x[1], reverse=True)
    return [(zodiac, count, count/total*100 if total > 0 else 0) for zodiac, count in sorted_zodiac]

def calculate_zodiac_consecutive(region):
    """
    计算3连肖组合出现频率
    3连肖：指连续3期开奖结果中，生肖的组合关系
    """
    results = get_all_draw_results(region)
    consecutive_triples = Counter()
    
    zodiac_list = []
    for row in results:
        special_num = row[1]
        for zodiac, numbers in ZODIAC_MAP.items():
            if special_num in numbers:
                zodiac_list.append(zodiac)
                break
    
    for i in range(len(zodiac_list) - 2):
        triple = tuple(sorted([zodiac_list[i], zodiac_list[i+1], zodiac_list[i+2]]))
        consecutive_triples[triple] += 1
    
    total = len(zodiac_list) - 2 if len(zodiac_list) > 2 else 1
    sorted_triples = sorted(consecutive_triples.items(), key=lambda x: x[1], reverse=True)
    return [(triple, count, count/total*100 if total > 0 else 0) for triple, count in sorted_triples]

def calculate_special_zodiac_frequency(region):
    """
    计算特码生肖出现频率
    """
    results = get_all_draw_results(region)
    zodiac_counts = Counter()
    
    for row in results:
        special_num = row[1]
        for zodiac, numbers in ZODIAC_MAP.items():
            if special_num in numbers:
                zodiac_counts[zodiac] += 1
                break
    
    total = sum(zodiac_counts.values())
    sorted_zodiac = sorted(zodiac_counts.items(), key=lambda x: x[1], reverse=True)
    return [(zodiac, count, count/total*100 if total > 0 else 0) for zodiac, count in sorted_zodiac]

def calculate_triple_zodiac_cooccurrence(region):
    """
    计算三肖组合共现频率
    """
    results = get_all_draw_results(region)
    zodiac_list = []
    
    for row in results:
        special_num = row[1]
        for zodiac, numbers in ZODIAC_MAP.items():
            if special_num in numbers:
                zodiac_list.append(zodiac)
                break
    
    triple_counts = Counter()
    for i in range(len(zodiac_list) - 2):
        triples = combinations(sorted([zodiac_list[i], zodiac_list[i+1], zodiac_list[i+2]]), 3)
        for triple in triples:
            triple_counts[triple] += 1
    
    total = len(zodiac_list) - 2 if len(zodiac_list) > 2 else 1
    sorted_triples = sorted(triple_counts.items(), key=lambda x: x[1], reverse=True)
    return [(triple, count, count/total*100 if total > 0 else 0) for triple, count in sorted_triples]

def generate_prediction(region, issue):
    number_freq = calculate_number_frequency(region)
    zodiac_freq = calculate_zodiac_frequency(region)
    special_zodiac_freq = calculate_special_zodiac_frequency(region)
    triple_cooccur = calculate_triple_zodiac_cooccurrence(region)
    consecutive_triples = calculate_zodiac_consecutive(region)
    total_count = get_total_draw_count(region)
    
    top_6_numbers = number_freq[:6]
    top_12_numbers = number_freq[:12]
    top_4_triples = triple_cooccur[:4]
    top_6_special_zodiac = special_zodiac_freq[:6]
    top_4_consecutive = consecutive_triples[:4]
    
    special_6_pred = []
    for num, freq, prob in top_6_numbers:
        zodiac = None
        for z, nums in ZODIAC_MAP.items():
            if num in nums:
                zodiac = z
                break
        special_6_pred.append({
            'number': num, 
            'zodiac': zodiac, 
            'frequency': freq,
            'probability': round(prob, 2),
            'basis': f'历史出现{freq}次，概率{prob:.2f}%'
        })
    
    triple_pred = []
    for triple, count, prob in top_4_triples:
        zodiacs = list(triple)
        numbers = []
        for z in zodiacs:
            numbers.extend(ZODIAC_MAP[z])
        triple_pred.append({
            'zodiacs': zodiacs, 
            'numbers': sorted(numbers), 
            'frequency': count,
            'probability': round(prob, 2),
            'basis': f'组合出现{count}次，概率{prob:.2f}%'
        })
    
    hot_12_pred = []
    for num, freq, prob in top_12_numbers:
        zodiac = None
        for z, nums in ZODIAC_MAP.items():
            if num in nums:
                zodiac = z
                break
        hot_12_pred.append({
            'number': num, 
            'zodiac': zodiac, 
            'frequency': freq,
            'probability': round(prob, 2)
        })
    
    special_6_zodiac_pred = []
    for zodiac, count, prob in top_6_special_zodiac:
        numbers = ZODIAC_MAP[zodiac]
        special_6_zodiac_pred.append({
            'zodiac': zodiac,
            'numbers': numbers,
            'frequency': count,
            'probability': round(prob, 2),
            'basis': f'生肖{count}期未出现，概率{prob:.2f}%'
        })
    
    consecutive_pred = []
    for triple, count, prob in top_4_consecutive:
        zodiacs = list(triple)
        numbers = []
        for z in zodiacs:
            numbers.extend(ZODIAC_MAP[z])
        consecutive_pred.append({
            'zodiacs': zodiacs,
            'numbers': sorted(numbers),
            'frequency': count,
            'probability': round(prob, 2),
            'basis': f'3连肖出现{count}次，概率{prob:.2f}%'
        })
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM predictions WHERE region = ? AND issue = ?', (region, issue))
    
    cursor.execute('''
        INSERT INTO predictions (region, issue, pred_type, content)
        VALUES (?, ?, ?, ?)
    ''', (region, issue, 'special_6', str(special_6_pred)))
    
    cursor.execute('''
        INSERT INTO predictions (region, issue, pred_type, content)
        VALUES (?, ?, ?, ?)
    ''', (region, issue, 'triple_zodiac', str(triple_pred)))
    
    cursor.execute('''
        INSERT INTO predictions (region, issue, pred_type, content)
        VALUES (?, ?, ?, ?)
    ''', (region, issue, 'hot_12', str(hot_12_pred)))
    
    cursor.execute('''
        INSERT INTO predictions (region, issue, pred_type, content)
        VALUES (?, ?, ?, ?)
    ''', (region, issue, 'special_6_zodiac', str(special_6_zodiac_pred)))
    
    cursor.execute('''
        INSERT INTO predictions (region, issue, pred_type, content)
        VALUES (?, ?, ?, ?)
    ''', (region, issue, 'consecutive_3_zodiac', str(consecutive_pred)))
    
    conn.commit()
    conn.close()
    
    return {
        'region': region,
        'issue': issue,
        'model_version': PREDICTION_MODEL_VERSION,
        'total_draws': total_count,
        'special_6': special_6_pred,
        'triple_zodiac': triple_pred,
        'hot_12': hot_12_pred,
        'special_6_zodiac': special_6_zodiac_pred,
        'consecutive_3_zodiac': consecutive_pred
    }

def get_prediction(region, issue):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT pred_type, content, actual_special, is_correct, accuracy FROM predictions WHERE region = ? AND issue = ?', (region, issue))
    results = cursor.fetchall()
    conn.close()
    
    pred_data = {}
    for pred_type, content, actual_special, is_correct, accuracy in results:
        pred_data[pred_type] = {
            'content': eval(content),
            'actual_special': actual_special,
            'is_correct': is_correct,
            'accuracy': accuracy
        }
    
    return pred_data

if __name__ == '__main__':
    pred = generate_prediction('am', '2024001')
    print('预测生成完成')
    print('特码6只:', pred['special_6'])
    print('三肖组合:', pred['triple_zodiac'])
    print('6肖特码:', pred['special_6_zodiac'])
    print('3连肖:', pred['consecutive_3_zodiac'])
