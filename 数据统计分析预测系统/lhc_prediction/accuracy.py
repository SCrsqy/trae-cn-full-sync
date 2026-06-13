import sqlite3
from config import DATABASE_PATH, ZODIAC_MAP

def update_accuracy(region, issue, actual_special):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, pred_type, content FROM predictions WHERE region = ? AND issue = ?', (region, issue))
    predictions = cursor.fetchall()
    
    for pred_id, pred_type, content in predictions:
        content_data = eval(content)
        is_correct = 0
        numbers = []
        
        if pred_type == 'special_6':
            numbers = [item['number'] for item in content_data]
        elif pred_type == 'triple_zodiac':
            for triple in content_data:
                numbers.extend(triple['numbers'])
        elif pred_type == 'hot_12':
            numbers = [item['number'] for item in content_data]
        
        if actual_special in numbers:
            is_correct = 1
        
        cursor.execute('UPDATE predictions SET actual_special = ?, is_correct = ? WHERE id = ?', 
                      (actual_special, is_correct, pred_id))
    
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE region = ?', (region,))
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM predictions WHERE region = ? AND is_correct = 1', (region,))
    correct = cursor.fetchone()[0]
    
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    cursor.execute('UPDATE predictions SET accuracy = ? WHERE region = ?', (accuracy, region))
    
    conn.commit()
    conn.close()
    
    return accuracy

def get_accuracy_summary(region):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT pred_type, 
               COUNT(*) as total, 
               SUM(is_correct) as correct,
               AVG(accuracy) as avg_accuracy
        FROM predictions 
        WHERE region = ? 
        GROUP BY pred_type
    ''', (region,))
    
    results = cursor.fetchall()
    conn.close()
    
    summary = {}
    for pred_type, total, correct, avg_accuracy in results:
        summary[pred_type] = {
            'total': total,
            'correct': correct,
            'accuracy': (correct / total) * 100 if total > 0 else 0,
            'avg_accuracy': avg_accuracy
        }
    
    return summary

def get_all_predictions(region):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT issue, pred_type, content, actual_special, is_correct, accuracy, created_at
        FROM predictions 
        WHERE region = ? 
        ORDER BY issue DESC
    ''', (region,))
    
    results = cursor.fetchall()
    conn.close()
    
    predictions = []
    for issue, pred_type, content, actual_special, is_correct, accuracy, created_at in results:
        predictions.append({
            'issue': issue,
            'pred_type': pred_type,
            'content': eval(content),
            'actual_special': actual_special,
            'is_correct': is_correct,
            'accuracy': accuracy,
            'created_at': created_at
        })
    
    return predictions

def calculate_investment(region, bet_amount, odds):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT issue, content, actual_special, is_correct
        FROM predictions 
        WHERE region = ? AND pred_type = 'special_6'
    ''', (region,))
    
    results = cursor.fetchall()
    
    investment_records = []
    total_investment = 0
    total_return = 0
    total_net_profit = 0
    
    for issue, content, actual_special, is_correct in results:
        content_data = eval(content)
        pred_numbers = [item['number'] for item in content_data]
        
        investment = 6 * bet_amount
        return_amount = odds * bet_amount if is_correct else 0
        net_profit = return_amount - investment
        
        total_investment += investment
        total_return += return_amount
        total_net_profit += net_profit
        
        investment_records.append({
            'issue': issue,
            'bet_amount': bet_amount,
            'odds': odds,
            'pred_numbers': pred_numbers,
            'actual_special': actual_special,
            'is_won': is_correct,
            'investment': investment,
            'return_amount': return_amount,
            'net_profit': net_profit
        })
        
        cursor.execute('''
            INSERT OR REPLACE INTO investment_records 
            (region, issue, bet_amount, odds, pred_numbers, actual_special, 
             is_won, investment, return_amount, net_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (region, issue, bet_amount, odds, str(pred_numbers), actual_special,
              is_correct, investment, return_amount, net_profit))
    
    conn.commit()
    conn.close()
    
    return {
        'records': investment_records,
        'summary': {
            'total_investment': total_investment,
            'total_return': total_return,
            'total_net_profit': total_net_profit,
            'roi': (total_net_profit / total_investment) * 100 if total_investment > 0 else 0
        }
    }

if __name__ == '__main__':
    accuracy = update_accuracy('am', '2024001', 7)
    print(f'准确率: {accuracy:.2f}%')
    
    summary = get_accuracy_summary('am')
    print('准确率汇总:', summary)