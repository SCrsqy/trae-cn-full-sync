"""
Airflow DAG配置文件
实现完整的定时任务调度：爬虫、预测生成、准确率计算、Excel导出
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': ['admin@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}

# =====================================================
# 5.1.1 澳门数据抓取DAG
# =====================================================
with DAG(
    'lottery_am_daily',
    default_args=default_args,
    schedule_interval='0 22 * * *',
    catchup=False,
    tags=['lottery', 'am', 'crawl']
) as dag_am:
    
    crawl_task = PythonOperator(
        task_id='crawl_am',
        python_callable=lambda: run_crawl('AM'),
        dag=dag_am,
    )
    
    clean_task = PythonOperator(
        task_id='clean_am',
        python_callable=lambda: run_clean('AM'),
        dag=dag_am,
    )
    
    update_stats_task = PythonOperator(
        task_id='update_stats_am',
        python_callable=lambda: update_statistics('AM'),
        dag=dag_am,
    )
    
    crawl_task >> clean_task >> update_stats_task

# =====================================================
# 5.1.2 香港数据抓取DAG
# =====================================================
with DAG(
    'lottery_hk_daily',
    default_args=default_args,
    schedule_interval='0 22 * * *',
    catchup=False,
    tags=['lottery', 'hk', 'crawl']
) as dag_hk:
    
    crawl_task = PythonOperator(
        task_id='crawl_hk',
        python_callable=lambda: run_crawl('HK'),
        dag=dag_hk,
    )
    
    clean_task = PythonOperator(
        task_id='clean_hk',
        python_callable=lambda: run_clean('HK'),
        dag=dag_hk,
    )
    
    update_stats_task = PythonOperator(
        task_id='update_stats_hk',
        python_callable=lambda: update_statistics('HK'),
        dag=dag_hk,
    )
    
    crawl_task >> clean_task >> update_stats_task

# =====================================================
# 5.1.3 预测生成DAG（每日07:00）
# =====================================================
with DAG(
    'predict_daily',
    default_args=default_args,
    schedule_interval='0 7 * * *',
    catchup=False,
    tags=['lottery', 'prediction']
) as dag_predict:
    
    gen_am_task = PythonOperator(
        task_id='gen_pred_am',
        python_callable=lambda: generate_and_save_prediction('AM'),
        dag=dag_predict,
    )
    
    gen_hk_task = PythonOperator(
        task_id='gen_pred_hk',
        python_callable=lambda: generate_and_save_prediction('HK'),
        dag=dag_predict,
    )
    
    export_excel_task = PythonOperator(
        task_id='export_excel',
        python_callable=export_to_excel,
        dag=dag_predict,
    )
    
    gen_am_task >> gen_hk_task >> export_excel_task

# =====================================================
# 5.1.4 准确率重算DAG（每5分钟）
# =====================================================
with DAG(
    'recalc_accuracy',
    default_args=default_args,
    schedule_interval='*/5 * * * *',
    catchup=False,
    tags=['lottery', 'accuracy']
) as dag_recalc:
    
    check_task = PythonOperator(
        task_id='check_pending',
        python_callable=recalc_pending_accuracy,
        dag=dag_recalc,
    )
    
    notify_task = PythonOperator(
        task_id='notify_low_accuracy',
        python_callable=check_low_accuracy_alert,
        dag=dag_recalc,
    )
    
    check_task >> notify_task

# =====================================================
# 5.1.5 每日Excel导出DAG（每日10:00）
# =====================================================
with DAG(
    'daily_excel_export',
    default_args=default_args,
    schedule_interval='0 10 * * *',
    catchup=False,
    tags=['lottery', 'excel']
) as dag_excel:
    
    export_task = PythonOperator(
        task_id='daily_export',
        python_callable=export_to_excel,
        dag=dag_excel,
    )

# =====================================================
# 任务执行函数
# =====================================================
def run_crawl(source_id):
    """执行爬虫任务"""
    import subprocess
    result = subprocess.run(
        ['python3', '/Users/rs/AI/分析预测推荐/data_sources.py', '--crawl', source_id],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"爬虫执行失败: {result.stderr}")
    return result.stdout

def run_clean(source_id):
    """执行数据清洗"""
    import subprocess
    result = subprocess.run(
        ['python3', '-c', f'''
from data_sources import DataSourceCrawler
crawler = DataSourceCrawler()
crawler.clean_data('{source_id}')
print("数据清洗完成")
'''],
        capture_output=True,
        text=True,
        cwd='/Users/rs/AI/分析预测推荐'
    )
    if result.returncode != 0:
        raise Exception(f"数据清洗失败: {result.stderr}")
    return result.stdout

def update_statistics(source_id):
    """更新统计数据"""
    import subprocess
    result = subprocess.run(
        ['python3', '-c', f'''
from time_weighted_analyzer import TimeWeightedAnalyzer
analyzer = TimeWeightedAnalyzer()
analyzer.update_statistics('{source_id}')
print("统计更新完成")
'''],
        capture_output=True,
        text=True,
        cwd='/Users/rs/AI/分析预测推荐'
    )
    if result.returncode != 0:
        raise Exception(f"统计更新失败: {result.stderr}")
    return result.stdout

def generate_and_save_prediction(source_id):
    """生成并保存预测"""
    from business_rules import PredictionGenerator
    
    generator = PredictionGenerator('/Users/rs/AI/分析预测推荐/lottery.db')
    prediction = generator.generate_prediction(source_id)
    print(f"生成{source_id}预测: {prediction.issue_number}")
    return prediction.issue_number

def export_to_excel():
    """导出Excel报告"""
    from report_generator import ReportGenerator
    
    generator = ReportGenerator(
        db_path='/Users/rs/AI/分析预测推荐/lottery.db',
        output_path='/Users/rs/AI/分析预测推荐/统计分析预测报告.xlsx',
        sources=['AM', 'HK']
    )
    success = generator.generate_report()
    
    if not success:
        raise Exception("Excel导出失败")
    print("Excel导出完成")
    return success

def recalc_pending_accuracy():
    """检查并重新计算未计算准确率的预测"""
    from business_rules import AccuracyCalculator
    
    calculator = AccuracyCalculator('/Users/rs/AI/分析预测推荐/lottery.db')
    
    updated_am = calculator.batch_update_accuracy('AM')
    updated_hk = calculator.batch_update_accuracy('HK')
    
    print(f"更新准确率: AM={updated_am}, HK={updated_hk}")
    return {'am_updated': updated_am, 'hk_updated': updated_hk}

def check_low_accuracy_alert():
    """检查准确率是否连续5期低于30%"""
    import sqlite3
    
    conn = sqlite3.connect('/Users/rs/AI/分析预测推荐/lottery.db')
    cursor = conn.cursor()
    
    for source in ['AM', 'HK']:
        cursor.execute(f"""
            SELECT accuracy_rate FROM predictions_{source.lower()}
            WHERE accuracy_rate IS NOT NULL
            ORDER BY issue_number DESC
            LIMIT 5
        """)
        
        rates = [row[0] for row in cursor.fetchall()]
        
        if len(rates) >= 5 and all(r < 30 for r in rates):
            print(f"警告: {source}连续5期准确率低于30%")
            # 发送邮件通知
            send_alert_email(source, rates)
    
    conn.close()

def send_alert_email(source, rates):
    """发送告警邮件"""
    import smtplib
    from email.mime.text import MIMEText
    
    content = f"""
    警告：{source}数据源准确率异常
    
    最近5期准确率: {rates}
    
    所有准确率均低于30%，请分析师关注！
    """
    
    msg = MIMEText(content)
    msg['Subject'] = f'【告警】{source}准确率异常'
    msg['From'] = 'admin@example.com'
    msg['To'] = 'analyst@example.com'
    
    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg)
        print("告警邮件已发送")
    except Exception as e:
        print(f"发送邮件失败: {e}")