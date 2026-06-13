from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from io import BytesIO
from datetime import datetime
import os

app = Flask(__name__)

from config import DATABASE_PATH
from models import init_database, get_db_connection
from crawler import crawl
from analyzer import generate_prediction, get_prediction, calculate_number_frequency
from accuracy import update_accuracy, get_accuracy_summary, get_all_predictions, calculate_investment
from auto_export import get_latest_draw_records, get_latest_prediction, get_next_prediction, update_excel_file, export_daily_report

init_database()

scheduler = None

def init_scheduler():
    global scheduler
    from scheduler import Scheduler
    scheduler = Scheduler()
    scheduler.start()

@app.before_request
def before_first_request():
    global scheduler
    if scheduler is None:
        init_scheduler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/crawl', methods=['POST'])
def api_crawl():
    region = request.json.get('region')
    use_mock = request.json.get('use_mock', True)
    try:
        count = crawl(region, use_mock=use_mock)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/predict', methods=['POST'])
def api_predict():
    region = request.json.get('region')
    issue = request.json.get('issue')
    try:
        prediction = generate_prediction(region, issue)
        return jsonify({'success': True, 'data': prediction})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prediction/<region>/<issue>', methods=['GET'])
def api_get_prediction(region, issue):
    try:
        prediction = get_prediction(region, issue)
        return jsonify({'success': True, 'data': prediction})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_accuracy', methods=['POST'])
def api_update_accuracy():
    region = request.json.get('region')
    issue = request.json.get('issue')
    actual_special = request.json.get('actual_special')
    try:
        accuracy = update_accuracy(region, issue, actual_special)
        return jsonify({'success': True, 'accuracy': accuracy})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/accuracy_summary/<region>', methods=['GET'])
def api_accuracy_summary(region):
    try:
        summary = get_accuracy_summary(region)
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/all_predictions/<region>', methods=['GET'])
def api_all_predictions(region):
    try:
        predictions = get_all_predictions(region)
        return jsonify({'success': True, 'data': predictions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/investment', methods=['POST'])
def api_investment():
    region = request.json.get('region')
    bet_amount = request.json.get('bet_amount', 10)
    odds = request.json.get('odds', 45)
    try:
        result = calculate_investment(region, bet_amount, odds)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/export_excel/<region>', methods=['POST'])
def api_export_excel(region):
    bet_amount = request.json.get('bet_amount', 10)
    odds = request.json.get('odds', 45)
    
    try:
        predictions = get_all_predictions(region)
        investment = calculate_investment(region, bet_amount, odds)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pred_df = pd.DataFrame(predictions)
            pred_df.to_excel(writer, sheet_name=f'{region}_predictions', index=False)
            
            if investment['records']:
                inv_df = pd.DataFrame(investment['records'])
                inv_df.to_excel(writer, sheet_name=f'{region}_investment', index=False)
                
                summary_df = pd.DataFrame([investment['summary']])
                summary_df.to_excel(writer, sheet_name=f'{region}_summary', index=False)
        
        output.seek(0)
        return send_file(output, download_name=f'{region}_predictions.xlsx', as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/latest_records/<region>', methods=['GET'])
def api_latest_records(region):
    try:
        draw_records = get_latest_draw_records(region, 1)
        pred_records = get_latest_prediction(region, 1)
        next_preds = get_next_prediction(region)
        return jsonify({
            'success': True,
            'data': {
                'draw': draw_records[0] if draw_records else None,
                'prediction': pred_records[0] if pred_records else None,
                'next_prediction': next_preds.get(list(next_preds.keys())[0]) if next_preds else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/latest_records_all', methods=['GET'])
def api_latest_records_all():
    try:
        am_draw = get_latest_draw_records('am', 1)
        hk_draw = get_latest_draw_records('hk', 1)
        am_pred = get_latest_prediction('am', 1)
        hk_pred = get_latest_prediction('hk', 1)
        am_next = get_next_prediction('am')
        hk_next = get_next_prediction('hk')
        
        return jsonify({
            'success': True,
            'data': {
                'am': {
                    'draw': am_draw[0] if am_draw else None,
                    'prediction': am_pred[0] if am_pred else None,
                    'next_prediction': am_next.get(list(am_next.keys())[0]) if am_next else None
                },
                'hk': {
                    'draw': hk_draw[0] if hk_draw else None,
                    'prediction': hk_pred[0] if hk_pred else None,
                    'next_prediction': hk_next.get(list(hk_next.keys())[0]) if hk_next else None
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard_data', methods=['GET'])
def api_dashboard_data():
    try:
        am_draw = get_latest_draw_records('am', 1)
        hk_draw = get_latest_draw_records('hk', 1)
        am_next = get_next_prediction('am')
        hk_next = get_next_prediction('hk')
        am_freq = calculate_number_frequency('am')
        hk_freq = calculate_number_frequency('hk')
        am_issue_range = get_issue_range('am')
        hk_issue_range = get_issue_range('hk')
        
        return jsonify({
            'success': True,
            'data': {
                'am': {
                    'last_draw': am_draw[0] if am_draw else None,
                    'next_issue': list(am_next.keys())[0] if am_next else None,
                    'next_prediction': am_next.get(list(am_next.keys())[0]) if am_next else None,
                    'frequency': am_freq[:12],
                    'issue_range': am_issue_range
                },
                'hk': {
                    'last_draw': hk_draw[0] if hk_draw else None,
                    'next_issue': list(hk_next.keys())[0] if hk_next else None,
                    'next_prediction': hk_next.get(list(hk_next.keys())[0]) if hk_next else None,
                    'frequency': hk_freq[:12],
                    'issue_range': hk_issue_range
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/export_all', methods=['POST'])
def api_export_all():
    bet_amount = request.json.get('bet_amount', 10)
    odds = request.json.get('odds', 45)
    
    try:
        update_excel_file()
        
        am_predictions = get_all_predictions('am')
        hk_predictions = get_all_predictions('hk')
        am_investment = calculate_investment('am', bet_amount, odds)
        hk_investment = calculate_investment('hk', bet_amount, odds)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            am_df = pd.DataFrame(am_predictions)
            am_df.to_excel(writer, sheet_name='澳门预测记录', index=False)
            
            hk_df = pd.DataFrame(hk_predictions)
            hk_df.to_excel(writer, sheet_name='香港预测记录', index=False)
            
            all_records = []
            all_records.extend([{'region': '澳门', **r} for r in am_investment['records']])
            all_records.extend([{'region': '香港', **r} for r in hk_investment['records']])
            inv_df = pd.DataFrame(all_records)
            inv_df.to_excel(writer, sheet_name='投资收益明细', index=False)
            
            summary_data = {
                '地区': ['澳门', '香港', '合计'],
                '总投入': [
                    am_investment['summary']['total_investment'],
                    hk_investment['summary']['total_investment'],
                    am_investment['summary']['total_investment'] + hk_investment['summary']['total_investment']
                ],
                '总回报': [
                    am_investment['summary']['total_return'],
                    hk_investment['summary']['total_return'],
                    am_investment['summary']['total_return'] + hk_investment['summary']['total_return']
                ],
                '净收益': [
                    am_investment['summary']['total_net_profit'],
                    hk_investment['summary']['total_net_profit'],
                    am_investment['summary']['total_net_profit'] + hk_investment['summary']['total_net_profit']
                ],
                '回报率': [
                    am_investment['summary']['roi'],
                    hk_investment['summary']['roi'],
                    ((am_investment['summary']['total_net_profit'] + hk_investment['summary']['total_net_profit']) / 
                     (am_investment['summary']['total_investment'] + hk_investment['summary']['total_investment']) * 100 
                     if (am_investment['summary']['total_investment'] + hk_investment['summary']['total_investment']) > 0 else 0)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='投资收益汇总', index=False)
        
        output.seek(0)
        return send_file(output, download_name='lhc_predictions_all.xlsx', as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scheduler_status', methods=['GET'])
def api_scheduler_status():
    if scheduler:
        return jsonify({'success': True, 'data': scheduler.get_status()})
    return jsonify({'success': False, 'error': '调度器未启动'})

@app.route('/api/trigger_task', methods=['POST'])
def api_trigger_task():
    if scheduler:
        scheduler.trigger_manual_run()
        return jsonify({'success': True, 'message': '手动任务已触发'})
    return jsonify({'success': False, 'error': '调度器未启动'})

@app.route('/api/execution_logs', methods=['GET'])
def api_execution_logs():
    if scheduler:
        try:
            limit = request.args.get('limit', 20, type=int)
            logs = scheduler.get_recent_logs(limit)
            failed_logs = scheduler.get_failed_logs(7)
            
            logs_data = [{
                'id': log[0],
                'task_name': log[1],
                'start_time': log[2],
                'end_time': log[3],
                'status': log[4],
                'data_count': log[5],
                'error_message': log[6]
            } for log in logs]
            
            failed_data = [{
                'id': log[0],
                'task_name': log[1],
                'start_time': log[2],
                'end_time': log[3],
                'status': log[4],
                'error_message': log[5]
            } for log in failed_logs]
            
            return jsonify({
                'success': True,
                'data': {
                    'recent_logs': logs_data,
                    'failed_logs': failed_data
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '调度器未启动'})

@app.route('/api/backup_list', methods=['GET'])
def api_backup_list():
    if scheduler:
        try:
            backups = scheduler.system_updater.get_available_backups()
            backups_data = [{
                'name': b['name'],
                'path': b['path'],
                'time': datetime.fromtimestamp(b['time']).strftime('%Y-%m-%d %H:%M:%S')
            } for b in backups]
            return jsonify({'success': True, 'data': backups_data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '调度器未启动'})

@app.route('/api/rollback', methods=['POST'])
def api_rollback():
    if scheduler:
        try:
            backup_name = request.json.get('backup_name')
            if not backup_name:
                return jsonify({'success': False, 'error': '缺少备份名称'})
            
            success = scheduler.rollback_to_backup(backup_name)
            if success:
                return jsonify({'success': True, 'message': '回滚成功'})
            else:
                return jsonify({'success': False, 'error': '回滚失败'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '调度器未启动'})

if __name__ == '__main__':
    init_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)