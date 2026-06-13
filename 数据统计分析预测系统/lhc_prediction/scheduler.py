"""
增强版自动化数据处理系统调度器
功能：
- 每天21:45自动执行数据抓取与处理
- 网络异常处理与重试机制
- Excel文件整合
- 详细日志记录
- 系统更新与回滚
"""

import threading
import time
import sqlite3
import logging
import os
import shutil
import json
from datetime import datetime, timedelta
from config import DATABASE_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExecutionLog:
    """任务执行日志管理"""
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_log_table()
    
    def _init_log_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                data_count INTEGER DEFAULT 0,
                error_message TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def log_start(self, task_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO execution_logs (task_name, start_time, status)
            VALUES (?, ?, ?)
        ''', (task_name, datetime.now().isoformat(), 'running'))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    
    def log_end(self, log_id, status, data_count=0, error_message=None, details=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE execution_logs 
            SET end_time = ?, status = ?, data_count = ?, error_message = ?, details = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), status, data_count, error_message, details, log_id))
        conn.commit()
        conn.close()
    
    def get_recent_logs(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, task_name, start_time, end_time, status, data_count, error_message
            FROM execution_logs
            ORDER BY start_time DESC
            LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_failed_logs(self, days=7):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, task_name, start_time, end_time, status, error_message
            FROM execution_logs
            WHERE status = 'failed' AND start_time >= datetime('now', '-' || ? || ' days')
            ORDER BY start_time DESC
        ''', (days,))
        results = cursor.fetchall()
        conn.close()
        return results

class NetworkHandler:
    """网络请求处理器，支持重试机制"""
    def __init__(self, max_retries=3, retry_delay=5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def fetch_with_retry(self, url, headers=None, timeout=30):
        import requests
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"正在尝试获取数据 (第{attempt}次): {url}")
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                logger.info(f"成功获取数据: {url}")
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"获取数据失败 (第{attempt}次): {str(e)}")
                if attempt < self.max_retries:
                    logger.info(f"等待{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"达到最大重试次数，获取数据失败: {url}")
                    raise

class ExcelIntegrator:
    """Excel文件整合器"""
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.excel_path = os.path.join(base_dir, 'lhc_data.xlsx')
    
    def read_excel(self):
        """读取Excel文件"""
        import pandas as pd
        try:
            if os.path.exists(self.excel_path):
                df = pd.read_excel(self.excel_path)
                logger.info(f"成功读取Excel文件，共{len(df)}条记录")
                return df
            return None
        except Exception as e:
            logger.error(f"读取Excel文件失败: {str(e)}")
            return None
    
    def write_excel(self, data, sheet_name='data'):
        """写入Excel文件"""
        import pandas as pd
        try:
            with pd.ExcelWriter(self.excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                if isinstance(data, pd.DataFrame):
                    data.to_excel(writer, sheet_name=sheet_name, index=False)
                elif isinstance(data, dict):
                    for name, df in data.items():
                        if isinstance(df, pd.DataFrame):
                            df.to_excel(writer, sheet_name=name, index=False)
            logger.info(f"成功写入Excel文件: {self.excel_path}")
            return True
        except Exception as e:
            logger.error(f"写入Excel文件失败: {str(e)}")
            return False
    
    def append_data(self, new_data, sheet_name='data'):
        """追加数据到Excel"""
        import pandas as pd
        try:
            existing_data = self.read_excel()
            
            if existing_data is not None:
                combined_data = pd.concat([existing_data, new_data], ignore_index=True)
            else:
                combined_data = new_data
            
            return self.write_excel(combined_data, sheet_name)
        except Exception as e:
            logger.error(f"追加数据到Excel失败: {str(e)}")
            return False

class SystemUpdater:
    """系统更新与回滚"""
    def __init__(self, backup_dir):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, files):
        """创建备份"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.backup_dir, f'backup_{timestamp}')
            os.makedirs(backup_path, exist_ok=True)
            
            for file in files:
                if os.path.exists(file):
                    shutil.copy2(file, backup_path)
            
            logger.info(f"备份已创建: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            return None
    
    def rollback(self, backup_path):
        """回滚到指定备份"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"备份不存在: {backup_path}")
                return False
            
            for file in os.listdir(backup_path):
                src = os.path.join(backup_path, file)
                dst = os.path.join(os.path.dirname(backup_path.rstrip('/\\')), file)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
            
            logger.info(f"回滚完成: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"回滚失败: {str(e)}")
            return False
    
    def get_available_backups(self):
        """获取可用备份列表"""
        backups = []
        try:
            for item in os.listdir(self.backup_dir):
                path = os.path.join(self.backup_dir, item)
                if os.path.isdir(path):
                    backups.append({
                        'name': item,
                        'path': path,
                        'time': os.path.getctime(path)
                    })
            return sorted(backups, key=lambda x: x['time'], reverse=True)
        except Exception as e:
            logger.error(f"获取备份列表失败: {str(e)}")
            return []

class Scheduler:
    """主调度器类"""
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
        self.last_run_date = None
        self.last_run_status = {'am': None, 'hk': None}
        self.error_message = None
        self.log_handler = ExecutionLog(DATABASE_PATH)
        self.network_handler = NetworkHandler(max_retries=3, retry_delay=5)
        self.excel_integrator = ExcelIntegrator(os.path.dirname(DATABASE_PATH))
        self.system_updater = SystemUpdater(os.path.join(os.path.dirname(DATABASE_PATH), 'backups'))
        
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info('定时任务调度器已启动 (21:45执行)')
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info('定时任务调度器已停止')
        
    def _run_scheduler(self):
        while self.running:
            now = datetime.now()
            target_hour = 21
            target_minute = 45
            
            if now.hour == target_hour and now.minute == target_minute:
                if self.last_run_date != now.date():
                    self._execute_daily_task()
                    self.last_run_date = now.date()
            
            time.sleep(30)
    
    def _execute_daily_task(self):
        """执行每日任务"""
        logger.info("="*50)
        logger.info("开始执行每日定时任务...")
        
        log_id = self.log_handler.log_start('daily_data_task')
        start_time = datetime.now()
        
        task_results = {
            'crawl_am': {'success': False, 'count': 0},
            'crawl_hk': {'success': False, 'count': 0},
            'excel_sync': {'success': False},
            'system_update': {'success': False}
        }
        
        try:
            task_results['crawl_am'] = self._crawl_data('am')
            task_results['crawl_hk'] = self._crawl_data('hk')
            task_results['excel_sync'] = self._sync_to_excel()
            task_results['system_update'] = self._perform_system_update()
            
            total_count = task_results['crawl_am']['count'] + task_results['crawl_hk']['count']
            self.log_handler.log_end(log_id, 'success', total_count, details=json.dumps(task_results))
            
            logger.info(f"每日任务执行成功！共抓取{total_count}条数据")
            self._send_notification('success', f'任务完成！澳门{task_results["crawl_am"]["count"]}条，香港{task_results["crawl_hk"]["count"]}条')
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"每日任务执行失败: {error_msg}")
            self.log_handler.log_end(log_id, 'failed', error_message=error_msg, details=json.dumps(task_results))
            self._send_notification('error', f'任务失败: {error_msg}')
        
        logger.info("="*50)
    
    def _crawl_data(self, region):
        """爬取数据（带重试机制）"""
        from crawler import crawl
        
        try:
            logger.info(f"正在爬取{region}数据...")
            count = crawl(region)
            self.last_run_status[region] = {'success': True, 'count': count}
            logger.info(f"{region}数据爬取完成: {count}条")
            return {'success': True, 'count': count}
        except Exception as e:
            logger.error(f"{region}数据爬取失败: {str(e)}")
            self.last_run_status[region] = {'success': False, 'error': str(e)}
            return {'success': False, 'count': 0, 'error': str(e)}
    
    def _sync_to_excel(self):
        """同步数据到Excel"""
        try:
            import pandas as pd
            
            conn = sqlite3.connect(DATABASE_PATH)
            
            draw_df = pd.read_sql_query('SELECT * FROM draw_results ORDER BY draw_date DESC', conn)
            pred_df = pd.read_sql_query('SELECT * FROM predictions ORDER BY issue DESC', conn)
            
            conn.close()
            
            success = self.excel_integrator.write_excel({
                '开奖记录': draw_df,
                '预测记录': pred_df
            })
            
            logger.info(f"数据同步到Excel: {'成功' if success else '失败'}")
            return {'success': success}
        except Exception as e:
            logger.error(f"同步Excel失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _perform_system_update(self):
        """执行系统更新"""
        try:
            files_to_backup = [DATABASE_PATH, 'config.py']
            backup_path = self.system_updater.create_backup(files_to_backup)
            
            if backup_path:
                logger.info("系统更新：备份成功")
                return {'success': True, 'backup': backup_path}
            return {'success': False}
        except Exception as e:
            logger.error(f"系统更新失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _send_notification(self, status, message):
        """发送桌面通知"""
        try:
            import subprocess
            if status == 'success':
                script = f'display notification "{message}" with title "数据更新任务"'
            else:
                script = f'display notification "失败: {message}" with title "数据更新任务"'
            subprocess.run(['osascript', '-e', script], capture_output=True)
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    def _get_next_issue(self, region):
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
        return datetime.now().strftime('%Y001')
        
    def get_status(self):
        """获取调度器状态"""
        return {
            'running': self.running,
            'last_run_status': self.last_run_status,
            'error_message': self.error_message,
            'next_run_time': self._get_next_run_time(),
            'execution_logs': self.get_recent_logs(10)
        }
        
    def _get_next_run_time(self):
        """计算下次运行时间"""
        now = datetime.now()
        target_hour = 21
        target_minute = 45
        
        next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        return next_run.strftime('%Y-%m-%d %H:%M')
    
    def get_recent_logs(self, limit=10):
        """获取最近执行日志"""
        return self.log_handler.get_recent_logs(limit)
    
    def get_failed_logs(self, days=7):
        """获取失败日志"""
        return self.log_handler.get_failed_logs(days)
    
    def rollback_to_backup(self, backup_name):
        """回滚到指定备份"""
        backups = self.system_updater.get_available_backups()
        for backup in backups:
            if backup['name'] == backup_name:
                return self.system_updater.rollback(backup['path'])
        return False
    
    def trigger_manual_run(self):
        """手动触发任务"""
        threading.Thread(target=self._execute_daily_task, daemon=True).start()
        return {'message': '手动任务已触发'}

scheduler = Scheduler()
