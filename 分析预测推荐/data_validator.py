"""
数据完整性校验与质量保障模块
实现期号连续性、号码个数、农历生肖一致性、准确率自洽等校验规则
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 生肖映射（2026马年基准）
ZODIAC_NUMBER_MAP = {
    '鼠': [7, 19, 31, 43],
    '牛': [6, 18, 30, 42],
    '虎': [5, 17, 29, 41],
    '兔': [4, 16, 28, 40],
    '龙': [3, 15, 27, 39],
    '蛇': [2, 14, 26, 38],
    '马': [1, 13, 25, 37, 49],
    '羊': [12, 24, 36, 48],
    '猴': [11, 23, 35, 47],
    '鸡': [10, 22, 34, 46],
    '狗': [9, 21, 33, 45],
    '猪': [8, 20, 32, 44]
}

NUM_TO_ZODIAC = {}
for zodiac, numbers in ZODIAC_NUMBER_MAP.items():
    for num in numbers:
        NUM_TO_ZODIAC[num] = zodiac


class DataValidator:
    """数据完整性校验器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def validate_issue_continuity(self, source_id: str) -> Dict:
        """
        校验期号连续性：相邻期号差值应为1
        
        Returns:
            {'status': 'pass'/'warning'/'error', 'missing_issues': [], 'message': ''}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT issue_number FROM lottery_data_{source_id.lower()}
                ORDER BY CAST(REPLACE(issue_number, '期', '') AS INTEGER) ASC
            """)
            
            issues = [row[0] for row in cursor.fetchall()]
            
            if len(issues) < 2:
                return {'status': 'pass', 'missing_issues': [], 'message': '数据不足，跳过连续性检查'}
            
            missing = []
            prev_num = None
            
            for issue in issues:
                try:
                    num = int(issue.replace('期', ''))
                    if prev_num is not None and num - prev_num > 1:
                        for missing_num in range(prev_num + 1, num):
                            missing.append(f"{missing_num}期")
                    prev_num = num
                except:
                    continue
            
            if missing:
                logger.warning(f"期号不连续，缺少: {', '.join(missing)}")
                return {
                    'status': 'warning',
                    'missing_issues': missing,
                    'message': f"发现{len(missing)}个缺期"
                }
            
            return {
                'status': 'pass',
                'missing_issues': [],
                'message': '期号连续'
            }
        
        finally:
            conn.close()
    
    def validate_number_count(self, source_id: str) -> Dict:
        """
        校验号码个数：每期必须是7个号码
        
        Returns:
            {'status': 'pass'/'error', 'invalid_records': [], 'message': ''}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT issue_number, numbers FROM lottery_data_{source_id.lower()}
            """)
            
            invalid = []
            for row in cursor.fetchall():
                issue, numbers_str = row
                try:
                    numbers = json.loads(numbers_str) if isinstance(numbers_str, str) else numbers_str
                    if len(numbers) != 7:
                        invalid.append((issue, len(numbers)))
                except:
                    invalid.append((issue, '解析失败'))
            
            if invalid:
                logger.error(f"号码个数异常: {invalid}")
                return {
                    'status': 'error',
                    'invalid_records': invalid,
                    'message': f"发现{len(invalid)}条记录号码个数不符"
                }
            
            return {
                'status': 'pass',
                'invalid_records': [],
                'message': '所有记录号码个数正确'
            }
        
        finally:
            conn.close()
    
    def validate_zodiac_consistency(self, source_id: str) -> Dict:
        """
        校验农历生肖一致性：计算出的农历生肖年应与基准表匹配
        
        Returns:
            {'status': 'pass'/'error', 'mismatches': [], 'message': ''}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT issue_number, numbers, zodiacs, lunar_zodiac_year 
                FROM lottery_data_{source_id.lower()}
            """)
            
            mismatches = []
            for row in cursor.fetchall():
                issue, numbers_str, zodiacs_str, db_zodiac_year = row
                
                try:
                    numbers = json.loads(numbers_str) if isinstance(numbers_str, str) else numbers_str
                    zodiacs = json.loads(zodiacs_str) if isinstance(zodiacs_str, str) else zodiacs_str
                    
                    # 根据号码计算生肖
                    calculated_zodiacs = [NUM_TO_ZODIAC.get(n, '') for n in numbers]
                    
                    # 检查每个号码的生肖是否匹配
                    for num, actual_zodiac, expected_zodiac in zip(numbers, zodiacs, calculated_zodiacs):
                        if actual_zodiac != expected_zodiac and expected_zodiac:
                            mismatches.append({
                                'issue': issue,
                                'number': num,
                                'actual_zodiac': actual_zodiac,
                                'expected_zodiac': expected_zodiac
                            })
                except Exception as e:
                    mismatches.append({
                        'issue': issue,
                        'error': str(e)
                    })
            
            if mismatches:
                logger.error(f"生肖一致性校验失败: {mismatches}")
                return {
                    'status': 'error',
                    'mismatches': mismatches,
                    'message': f"发现{len(mismatches)}处生肖不匹配"
                }
            
            return {
                'status': 'pass',
                'mismatches': [],
                'message': '生肖一致性校验通过'
            }
        
        finally:
            conn.close()
    
    def validate_accuracy_consistency(self, source_id: str) -> Dict:
        """
        校验准确率自洽：综合准确率 ≈ 三单项加权和
        
        Returns:
            {'status': 'pass'/'warning', 'inconsistent_records': [], 'message': ''}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT issue_number, hit_rate_top6, hit_rate_triple4, hit_rate_top12, accuracy_rate
                FROM predictions_{source_id.lower()}
                WHERE accuracy_rate IS NOT NULL
            """)
            
            inconsistent = []
            for row in cursor.fetchall():
                issue, top6, triple4, top12, combined = row
                
                if None in [top6, triple4, top12, combined]:
                    continue
                
                # 计算预期综合准确率
                expected = top6 * 0.6 + triple4 * 0.3 + top12 * 0.1
                diff = abs(combined - expected)
                
                if diff > 0.01:
                    inconsistent.append({
                        'issue': issue,
                        'calculated': round(expected, 4),
                        'stored': combined,
                        'difference': round(diff, 4)
                    })
            
            if inconsistent:
                logger.warning(f"准确率自洽性校验失败: {inconsistent}")
                return {
                    'status': 'warning',
                    'inconsistent_records': inconsistent,
                    'message': f"发现{len(inconsistent)}条记录准确率不一致"
                }
            
            return {
                'status': 'pass',
                'inconsistent_records': [],
                'message': '准确率自洽性校验通过'
            }
        
        finally:
            conn.close()
    
    def run_all_validations(self, source_id: str) -> Dict:
        """运行所有校验"""
        logger.info(f"开始对 {source_id} 执行数据完整性校验...")
        
        results = {
            'source_id': source_id,
            'timestamp': datetime.now().isoformat(),
            'validations': {
                'issue_continuity': self.validate_issue_continuity(source_id),
                'number_count': self.validate_number_count(source_id),
                'zodiac_consistency': self.validate_zodiac_consistency(source_id),
                'accuracy_consistency': self.validate_accuracy_consistency(source_id)
            }
        }
        
        # 汇总结果
        statuses = [v['status'] for v in results['validations'].values()]
        overall_status = 'pass'
        
        if 'error' in statuses:
            overall_status = 'error'
        elif 'warning' in statuses:
            overall_status = 'warning'
        
        results['overall_status'] = overall_status
        
        logger.info(f"校验完成，总体状态: {overall_status}")
        return results
    
    def auto_fix_missing_issues(self, source_id: str):
        """自动尝试补爬缺期数据"""
        result = self.validate_issue_continuity(source_id)
        
        if result['status'] == 'warning' and result['missing_issues']:
            logger.info(f"尝试补爬缺期: {result['missing_issues']}")
            
            # 这里可以调用爬虫模块尝试补爬
            # 由于实际爬虫需要网络请求，这里只记录日志
            for issue in result['missing_issues']:
                logger.info(f"已标记需要补爬: {issue}")
            
            return result['missing_issues']
        
        return []


class DataBackup:
    """数据备份管理器"""
    
    def __init__(self, db_path: str, backup_dir: str = '/backup'):
        self.db_path = db_path
        self.backup_dir = backup_dir
    
    def backup(self, keep_days: int = 30):
        """执行全库备份"""
        import shutil
        import os
        
        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 生成备份文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'lottery_backup_{timestamp}.db')
        
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"备份成功: {backup_path}")
            
            # 清理过期备份
            self._clean_old_backups(keep_days)
            
            return {'status': 'success', 'backup_path': backup_path}
        
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _clean_old_backups(self, keep_days: int):
        """清理过期备份"""
        import os
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for filename in os.listdir(self.backup_dir):
            if filename.startswith('lottery_backup_') and filename.endswith('.db'):
                filepath = os.path.join(self.backup_dir, filename)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if mtime < cutoff_date:
                        os.remove(filepath)
                        logger.info(f"清理过期备份: {filename}")
                except Exception as e:
                    logger.warning(f"清理备份失败 {filename}: {e}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self, wechat_webhook: str = None):
        self.wechat_webhook = wechat_webhook
    
    def send_wechat_alert(self, title: str, content: str):
        """发送企业微信告警"""
        if not self.wechat_webhook:
            logger.warning("企业微信Webhook未配置")
            return
        
        try:
            import requests
            
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"【{title}】\n{content}"
                }
            }
            
            response = requests.post(self.wechat_webhook, json=payload)
            if response.status_code == 200:
                logger.info("企业微信告警发送成功")
            else:
                logger.error(f"企业微信告警发送失败: {response.text}")
        
        except Exception as e:
            logger.error(f"发送告警失败: {e}")
    
    def send_email_alert(self, to_email: str, subject: str, body: str):
        """发送邮件告警"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = 'lottery@example.com'
            msg['To'] = to_email
            
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)
            
            logger.info("邮件告警发送成功")
        
        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")


# 使用示例
if __name__ == "__main__":
    db_path = '/Users/rs/AI/分析预测推荐/lottery.db'
    
    # 创建校验器
    validator = DataValidator(db_path)
    
    # 执行校验
    results = validator.run_all_validations('AM')
    
    print("数据完整性校验报告")
    print("=" * 60)
    print(f"数据源: {results['source_id']}")
    print(f"时间: {results['timestamp']}")
    print(f"总体状态: {results['overall_status']}")
    print()
    
    for name, result in results['validations'].items():
        print(f"{name}:")
        print(f"  状态: {result['status']}")
        print(f"  消息: {result['message']}")
        if result.get('missing_issues'):
            print(f"  缺期: {', '.join(result['missing_issues'])}")
        if result.get('invalid_records'):
            print(f"  异常记录数: {len(result['invalid_records'])}")
        if result.get('mismatches'):
            print(f"  不匹配数: {len(result['mismatches'])}")
        print()
    
    # 测试备份
    backup = DataBackup(db_path, backup_dir='/tmp/lottery_backup')
    backup_result = backup.backup()
    print(f"备份结果: {backup_result}")