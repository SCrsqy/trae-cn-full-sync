"""
Flask后端服务
提供REST API和WebSocket实时更新推送
"""
import json
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'lottery-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = '/Users/rs/AI/分析预测推荐/lottery.db'


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/predictions/<source>', methods=['GET'])
def get_predictions(source):
    """获取预测数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT * FROM predictions_{source.lower()}
        ORDER BY issue_number DESC
        LIMIT 10
    """)
    
    predictions = []
    for row in cursor.fetchall():
        predictions.append({
            'issue_number': row['issue_number'],
            'top6_zodiacs': json.loads(row['top6_zodiacs']) if row['top6_zodiacs'] else [],
            'triple4_groups': json.loads(row['triple4_groups']) if row['triple4_groups'] else [],
            'top12_numbers': json.loads(row['top12_numbers']) if row['top12_numbers'] else [],
            'accuracy_rate': row['accuracy_rate'],
            'top6_accuracy': row['top6_accuracy'],
            'triple4_accuracy': row['triple4_accuracy'],
            'top12_accuracy': row['top12_accuracy'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return jsonify(predictions)


@app.route('/api/lottery_data/<source>', methods=['GET'])
def get_lottery_data(source):
    """获取开奖数据"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT COUNT(*) FROM lottery_data_{source.lower()}
    """)
    total = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT * FROM lottery_data_{source.lower()}
        ORDER BY issue_number DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    data = []
    for row in cursor.fetchall():
        data.append({
            'issue_number': row['issue_number'],
            'draw_date': row['draw_date'],
            'numbers': json.loads(row['numbers']) if row['numbers'] else [],
            'zodiacs': json.loads(row['zodiacs']) if row['zodiacs'] else [],
            'updated_at': row['updated_at']
        })
    
    conn.close()
    
    return jsonify({
        'data': data,
        'total': total,
        'page': page,
        'limit': limit
    })


@app.route('/api/statistics/<source>', methods=['GET'])
def get_statistics(source):
    """获取统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 计算数字频率
    cursor.execute(f"""
        SELECT numbers FROM lottery_data_{source.lower()}
    """)
    
    num_freq = {}
    for row in cursor.fetchall():
        numbers = json.loads(row['numbers']) if row['numbers'] else []
        for num in numbers:
            num_freq[num] = num_freq.get(num, 0) + 1
    
    # 计算生肖频率
    cursor.execute(f"""
        SELECT zodiacs FROM lottery_data_{source.lower()}
    """)
    
    zodiac_freq = {}
    for row in cursor.fetchall():
        zodiacs = json.loads(row['zodiacs']) if row['zodiacs'] else []
        for zodiac in zodiacs:
            zodiac_freq[zodiac] = zodiac_freq.get(zodiac, 0) + 1
    
    # 获取预测准确率统计
    cursor.execute(f"""
        SELECT AVG(accuracy_rate) as avg_acc, 
               MAX(accuracy_rate) as max_acc, 
               MIN(accuracy_rate) as min_acc,
               COUNT(*) as count
        FROM predictions_{source.lower()}
        WHERE accuracy_rate IS NOT NULL
    """)
    
    acc_stats = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'number_frequency': num_freq,
        'zodiac_frequency': zodiac_freq,
        'accuracy_stats': {
            'average': acc_stats['avg_acc'],
            'max': acc_stats['max_acc'],
            'min': acc_stats['min_acc'],
            'count': acc_stats['count']
        }
    })


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """获取数据源列表"""
    sources = [
        {'code': 'AM', 'name': '澳门', 'url': 'https://2026kj.zkclhb.com:2025/am.html#toubu13'},
        {'code': 'HK', 'name': '香港', 'url': 'https://2026kj.zkclhb.com:2025/hk.html#toubu13'}
    ]
    return jsonify(sources)


@app.route('/api/generate_prediction/<source>', methods=['POST'])
def generate_prediction(source):
    """生成预测"""
    try:
        from business_rules import PredictionGenerator
        
        generator = PredictionGenerator(DB_PATH)
        prediction = generator.generate_prediction(source)
        
        # 发送WebSocket通知
        socketio.emit('prediction_updated', {
            'source': source,
            'issue_number': prediction.issue_number,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({'success': True, 'issue_number': prediction.issue_number})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update_accuracy/<source>', methods=['POST'])
def update_accuracy(source):
    """更新准确率"""
    try:
        from business_rules import AccuracyCalculator
        
        calculator = AccuracyCalculator(DB_PATH)
        updated = calculator.batch_update_accuracy(source)
        
        # 发送WebSocket通知
        socketio.emit('accuracy_updated', {
            'source': source,
            'updated_count': updated,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({'success': True, 'updated_count': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export_report', methods=['GET'])
def export_report():
    """导出报告"""
    try:
        from report_generator import ReportGenerator
        
        generator = ReportGenerator(
            db_path=DB_PATH,
            output_path='/Users/rs/AI/分析预测推荐/统计分析预测报告.xlsx',
            sources=['AM', 'HK']
        )
        
        success = generator.generate_report()
        
        if success:
            return jsonify({'success': True, 'message': '报告生成成功'})
        else:
            return jsonify({'success': False, 'message': '报告生成失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    print('客户端已连接')
    emit('connected', {'message': '连接成功', 'timestamp': datetime.now().isoformat()})


@socketio.on('disconnect')
def handle_disconnect():
    """处理WebSocket断开"""
    print('客户端已断开连接')


@socketio.on('subscribe')
def handle_subscribe(data):
    """处理订阅请求"""
    channel = data.get('channel')
    print(f'客户端订阅频道: {channel}')
    emit('subscribed', {'channel': channel})


def send_update_notification(event_type, data):
    """发送更新通知"""
    socketio.emit('update', {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("启动Flask后端服务...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)