"""
核心业务规则模块
实现预测推荐格式、准确率计算等核心功能
适配新的数据库表结构
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

from lunar_zodiac import get_zodiac_for_number, zodiac_to_numbers, ZODIAC_ORDER, get_zodiac_for_date, get_lunar_year
from core_algorithm import (
    generate_prediction as core_generate_prediction,
    calculate_accuracy as core_calculate_accuracy,
    get_lunar_zodiac_year
)


class Prediction:
    """
    预测结果类
    包含特码6只、4组三肖、热门12数字
    适配新的数据库表结构
    """
    
    def __init__(self, issue_number: str):
        self.issue_number = issue_number
        self.top6_zodiacs = []  # [{"zodiac":"鼠","predicted_accuracy":78.5}, ...]
        self.triple4_groups = []  # [{"group":["鼠","龙","猴"],"numbers":[...]}, ...]
        self.top12_numbers = []  # [{"number":31,"zodiac":"鼠","frequency":12}, ...]
        self.predict_date = datetime.now().date()
        self.actual_result = None
        self.hit_rate_top6 = None  # 特肖6只命中率(%)
        self.hit_rate_triple4 = None  # 三肖4组命中率(%)
        self.hit_rate_top12 = None  # 热门12数字命中率(%)
        self.accuracy_rate = None  # 综合加权准确率(%)
        self.hit_status = None  # 详细命中情况
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'issue_number': self.issue_number,
            'top6_zodiacs': self.top6_zodiacs,
            'triple4_groups': self.triple4_groups,
            'top12_numbers': self.top12_numbers,
            'predict_date': self.predict_date.isoformat(),
            'hit_rate_top6': self.hit_rate_top6,
            'hit_rate_triple4': self.hit_rate_triple4,
            'hit_rate_top12': self.hit_rate_top12,
            'accuracy_rate': self.accuracy_rate,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PredictionGenerator:
    """
    预测生成器
    根据历史数据生成预测推荐
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.zodiac_numbers = {z: zodiac_to_numbers(z) for z in ZODIAC_ORDER}
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def load_all_history(self, source_id: str = 'AM') -> List[Dict]:
        """加载所有历史数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT issue_number, draw_date, numbers, zodiacs
                FROM lottery_data_{source_id.lower()}
                ORDER BY issue_number ASC
            """)
            
            results = []
            for row in cursor.fetchall():
                issue, date, numbers, zodiacs = row
                try:
                    numbers_list = json.loads(numbers) if isinstance(numbers, str) else numbers
                    zodiacs_list = json.loads(zodiacs) if isinstance(zodiacs, str) else zodiacs
                except:
                    continue
                
                results.append({
                    'issue_number': issue,
                    'draw_date': date,
                    'numbers': numbers_list,
                    'zodiacs': zodiacs_list
                })
            
            return results
        
        finally:
            conn.close()
    
    def calculate_zodiac_frequency(self, history: List[Dict]) -> Dict[str, int]:
        """计算生肖出现频率"""
        freq = defaultdict(int)
        
        for record in history:
            for zodiac in record['zodiacs']:
                freq[zodiac] += 1
        
        return dict(freq)
    
    def calculate_number_frequency(self, history: List[Dict]) -> Dict[int, int]:
        """计算数字出现频率"""
        freq = defaultdict(int)
        
        for record in history:
            for num in record['numbers']:
                freq[num] += 1
        
        return dict(freq)
    
    def calculate_triple_combo_frequency(self, history: List[Dict]) -> Dict[Tuple[str, str, str], int]:
        """计算三肖组合出现频率"""
        freq = defaultdict(int)
        
        for record in history:
            zodiacs = record['zodiacs']
            # 生成所有三肖组合
            for i in range(len(zodiacs)):
                for j in range(i + 1, len(zodiacs)):
                    for k in range(j + 1, len(zodiacs)):
                        combo = tuple(sorted([zodiacs[i], zodiacs[j], zodiacs[k]]))
                        freq[combo] += 1
        
        return dict(freq)
    
    def calculate_zodiac_accuracy(self, history: List[Dict]) -> Dict[str, float]:
        """计算每个生肖的历史命中率"""
        total_issues = len(history)
        if total_issues == 0:
            return {}
        
        hit_count = defaultdict(int)
        
        for record in history:
            for zodiac in record['zodiacs']:
                hit_count[zodiac] += 1
        
        # 计算命中率(出现次数/总期数)
        return {z: hit_count[z] / total_issues for z in ZODIAC_ORDER}
    
    def generate_top6_zodiacs(self, history: List[Dict]) -> List[Dict]:
        """
        生成特码6只生肖
        按历史命中准确率从高到低排序
        """
        zodiac_accuracy = self.calculate_zodiac_accuracy(history)
        
        # 按准确率排序
        sorted_zodiacs = sorted(ZODIAC_ORDER, key=lambda z: zodiac_accuracy.get(z, 0), reverse=True)
        
        # 取前6个
        top6 = []
        for zodiac in sorted_zodiacs[:6]:
            top6.append({
                'zodiac': zodiac,
                'numbers': self.zodiac_numbers[zodiac],
                'accuracy': zodiac_accuracy.get(zodiac, 0)
            })
        
        return top6
    
    def generate_triple4_groups(self, history: List[Dict]) -> List[Dict]:
        """
        生成4组三肖组合
        每组包含3个生肖及其对应的所有推荐数字
        """
        combo_freq = self.calculate_triple_combo_frequency(history)
        
        # 按频率排序
        sorted_combos = sorted(combo_freq.keys(), key=lambda c: combo_freq[c], reverse=True)
        
        # 选择不重叠的4组
        used_zodiacs = set()
        groups = []
        
        for combo in sorted_combos:
            if len(groups) >= 4:
                break
            
            # 检查是否有重叠
            if set(combo) & used_zodiacs:
                continue
            
            # 获取所有对应的数字
            all_numbers = []
            for zodiac in combo:
                all_numbers.extend(self.zodiac_numbers[zodiac])
            
            groups.append({
                'zodiacs': list(combo),
                'numbers': sorted(list(set(all_numbers))),
                'frequency': combo_freq[combo]
            })
            
            used_zodiacs.update(combo)
        
        # 如果不足4组，用剩余生肖补充
        if len(groups) < 4:
            remaining_zodiacs = [z for z in ZODIAC_ORDER if z not in used_zodiacs]
            while len(groups) < 4 and len(remaining_zodiacs) >= 3:
                new_group = remaining_zodiacs[:3]
                all_numbers = []
                for zodiac in new_group:
                    all_numbers.extend(self.zodiac_numbers[zodiac])
                
                groups.append({
                    'zodiacs': new_group,
                    'numbers': sorted(list(set(all_numbers))),
                    'frequency': 0
                })
                
                remaining_zodiacs = remaining_zodiacs[3:]
        
        return groups
    
    def generate_top12_numbers(self, history: List[Dict]) -> List[Dict]:
        """
        生成热门12个数字
        按出现频率最高排序，附带所属生肖
        """
        num_freq = self.calculate_number_frequency(history)
        
        # 按频率排序
        sorted_nums = sorted(num_freq.keys(), key=lambda n: num_freq[n], reverse=True)
        
        # 取前12个
        top12 = []
        for num in sorted_nums[:12]:
            top12.append({
                'number': num,
                'zodiac': get_zodiac_for_number(num),
                'frequency': num_freq[num]
            })
        
        return top12
    
    def generate_prediction(self, source_id: str = 'AM', issue_number: Optional[str] = None) -> Prediction:
        """
        生成完整预测（使用核心算法）
        
        Args:
            source_id: 数据源标识(AM/HK)
            issue_number: 期号，如果为空则自动生成下一期
        
        Returns:
            Prediction对象
        """
        # 使用核心算法生成预测
        core_pred = core_generate_prediction(self.db_path, source_id)
        
        # 自动生成下期期号
        if issue_number is None:
            history = self.load_all_history(source_id)
            if history:
                last_issue = history[-1]['issue_number']
                try:
                    num = int(last_issue.replace('期', ''))
                    issue_number = f"{num + 1}期"
                except:
                    issue_number = "1期"
            else:
                issue_number = "1期"
        
        # 创建预测对象
        prediction = Prediction(issue_number)
        
        # 填充预测数据
        prediction.top6_zodiacs = core_pred['top6']
        prediction.triple4_groups = core_pred['triple4']
        prediction.top12_numbers = core_pred['hot12']
        
        # 保存到数据库
        self.save_prediction(prediction, source_id)
        
        return prediction
    
    def save_prediction(self, prediction: Prediction, source_id: str):
        """保存预测到数据库（适配新表结构）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now()
            
            # 检查是否已存在
            cursor.execute(f"SELECT id FROM predictions_{source_id.lower()} WHERE issue_number = ?", 
                        (prediction.issue_number,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新
                cursor.execute(f"""
                    UPDATE predictions_{source_id.lower()}
                    SET top6_zodiacs = ?, triple4_groups = ?, top12_numbers = ?,
                        hit_rate_top6 = ?, hit_rate_triple4 = ?, hit_rate_top12 = ?,
                        accuracy_rate = ?, hit_status = ?, updated_at = ?
                    WHERE issue_number = ?
                """, (
                    json.dumps(prediction.top6_zodiacs),
                    json.dumps(prediction.triple4_groups),
                    json.dumps(prediction.top12_numbers),
                    prediction.hit_rate_top6,
                    prediction.hit_rate_triple4,
                    prediction.hit_rate_top12,
                    prediction.accuracy_rate,
                    json.dumps(prediction.hit_status) if prediction.hit_status else None,
                    now.isoformat(),
                    prediction.issue_number
                ))
            else:
                # 插入
                cursor.execute(f"""
                    INSERT INTO predictions_{source_id.lower()}
                    (issue_number, predict_date, top6_zodiacs, triple4_groups, top12_numbers,
                    hit_rate_top6, hit_rate_triple4, hit_rate_top12, accuracy_rate, hit_status,
                    created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction.issue_number,
                    prediction.predict_date.isoformat(),
                    json.dumps(prediction.top6_zodiacs),
                    json.dumps(prediction.triple4_groups),
                    json.dumps(prediction.top12_numbers),
                    prediction.hit_rate_top6,
                    prediction.hit_rate_triple4,
                    prediction.hit_rate_top12,
                    prediction.accuracy_rate,
                    json.dumps(prediction.hit_status) if prediction.hit_status else None,
                    now.isoformat(),
                    now.isoformat()
                ))
            
            conn.commit()
        
        finally:
            conn.close()


class AccuracyCalculator:
    """
    准确率计算器
    计算特肖6只、4组三肖、热门12数字的命中率
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def calculate_top6_accuracy(self, prediction: Dict, actual_zodiacs: List[str]) -> float:
        """
        计算特肖6只命中率
        
        Args:
            prediction: 预测数据(包含top6_zodiacs)
            actual_zodiacs: 实际开出的生肖列表
        
        Returns:
            命中率(0-1)
        """
        if not prediction or not actual_zodiacs:
            return 0.0
        
        predicted_zodiacs = [item['zodiac'] for item in prediction.get('top6_zodiacs', [])]
        
        # 计算命中数量
        hits = sum(1 for z in actual_zodiacs if z in predicted_zodiacs)
        
        # 命中率 = 命中数 / 实际开出数
        return hits / len(actual_zodiacs) if actual_zodiacs else 0.0
    
    def calculate_triple4_accuracy(self, prediction: Dict, actual_zodiacs: List[str]) -> float:
        """
        计算4组三肖命中率
        
        Args:
            prediction: 预测数据(包含triple4_groups)
            actual_zodiacs: 实际开出的生肖列表
        
        Returns:
            命中率(0-1)
        """
        if not prediction or not actual_zodiacs:
            return 0.0
        
        actual_set = set(actual_zodiacs)
        groups = prediction.get('triple4_groups', [])
        
        # 计算命中的组数量
        hit_groups = 0
        for group in groups:
            group_zodiacs = set(group.get('zodiacs', []))
            # 如果该组有至少一个生肖命中，视为该组命中
            if group_zodiacs & actual_set:
                hit_groups += 1
        
        # 命中率 = 命中组数 / 总组数
        return hit_groups / len(groups) if groups else 0.0
    
    def calculate_top12_accuracy(self, prediction: Dict, actual_numbers: List[int]) -> float:
        """
        计算热门12数字命中率
        
        Args:
            prediction: 预测数据(包含top12_numbers)
            actual_numbers: 实际开出的数字列表
        
        Returns:
            命中率(0-1)
        """
        if not prediction or not actual_numbers:
            return 0.0
        
        predicted_numbers = [item['number'] for item in prediction.get('top12_numbers', [])]
        
        # 计算命中数量
        hits = sum(1 for n in actual_numbers if n in predicted_numbers)
        
        # 命中率 = 命中数 / 实际开出数
        return hits / len(actual_numbers) if actual_numbers else 0.0
    
    def calculate_weighted_accuracy(self, top6_acc: float, triple4_acc: float, top12_acc: float) -> float:
        """
        计算综合加权准确率
        
        权重: 特肖6只×0.6 + 三肖×0.3 + 数字×0.1
        
        Args:
            top6_acc: 特肖准确率
            triple4_acc: 三肖准确率
            top12_acc: 数字准确率
        
        Returns:
            综合准确率(0-1)
        """
        return top6_acc * 0.6 + triple4_acc * 0.3 + top12_acc * 0.1
    
    def update_prediction_accuracy(self, issue_number: str, source_id: str = 'AM') -> bool:
        """
        更新预测的准确率
        
        Args:
            issue_number: 期号
            source_id: 数据源标识
        
        Returns:
            是否更新成功
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取预测数据
            cursor.execute(f"""
                SELECT top6_zodiacs, triple4_groups, top12_numbers
                FROM predictions_{source_id.lower()}
                WHERE issue_number = ?
            """, (issue_number,))
            
            pred_row = cursor.fetchone()
            if not pred_row:
                return False
            
            top6_str, triple4_str, top12_str = pred_row
            
            try:
                prediction = {
                    'top6_zodiacs': json.loads(top6_str),
                    'triple4_groups': json.loads(triple4_str),
                    'top12_numbers': json.loads(top12_str)
                }
            except:
                return False
            
            # 获取实际开奖数据
            cursor.execute(f"""
                SELECT numbers, zodiacs
                FROM lottery_data_{source_id.lower()}
                WHERE issue_number = ?
            """, (issue_number,))
            
            actual_row = cursor.fetchone()
            if not actual_row:
                return False
            
            numbers_str, zodiacs_str = actual_row
            
            try:
                actual_numbers = json.loads(numbers_str) if isinstance(numbers_str, str) else numbers_str
                actual_zodiacs = json.loads(zodiacs_str) if isinstance(zodiacs_str, str) else zodiacs_str
            except:
                return False
            
            # 使用核心算法计算准确率
            accuracy_result = core_calculate_accuracy(
                prediction, 
                actual_numbers, 
                actual_zodiacs
            )
            
            # 更新数据库（适配新字段名）
            cursor.execute(f"""
                UPDATE predictions_{source_id.lower()}
                SET hit_rate_top6 = ?, hit_rate_triple4 = ?, hit_rate_top12 = ?,
                    accuracy_rate = ?, hit_status = ?, updated_at = ?
                WHERE issue_number = ?
            """, (
                accuracy_result['hit_rate_top6'],
                accuracy_result['hit_rate_triple4'],
                accuracy_result['hit_rate_top12'],
                accuracy_result['accuracy_rate'],
                json.dumps(accuracy_result['hit_status']),
                datetime.now().isoformat(),
                issue_number
            ))
            
            conn.commit()
            return True
        
        finally:
            conn.close()
    
    def batch_update_accuracy(self, source_id: str = 'AM') -> int:
        """
        批量更新所有预测的准确率
        
        Args:
            source_id: 数据源标识
        
        Returns:
            更新的数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取所有未计算准确率的预测
            cursor.execute(f"""
                SELECT issue_number
                FROM predictions_{source_id.lower()}
                WHERE accuracy_rate IS NULL
            """)
            
            issues = [row[0] for row in cursor.fetchall()]
            updated_count = 0
            
            for issue in issues:
                if self.update_prediction_accuracy(issue, source_id):
                    updated_count += 1
            
            return updated_count
        
        finally:
            conn.close()


# 使用示例
if __name__ == "__main__":
    print("测试核心业务规则模块")
    print("=" * 50)
    
    # 测试预测生成器
    generator = PredictionGenerator('/Users/rs/AI/分析预测推荐/lottery.db')
    prediction = generator.generate_prediction('AM')
    
    print(f"期号: {prediction.issue_number}")
    print("\n特码6只生肖:")
    for i, item in enumerate(prediction.top6_zodiacs, 1):
        print(f"  {i}. {item['zodiac']} ({item['numbers']}) - 命中率: {item['predicted_accuracy']:.2f}%")
    
    print("\n4组三肖:")
    for i, group in enumerate(prediction.triple4_groups, 1):
        print(f"  第{i}组: {group['group']} -> {group['numbers']}")
    
    print("\n热门12数字:")
    for i, item in enumerate(prediction.top12_numbers, 1):
        print(f"  {i}. {item['number']} ({item['zodiac']}) - 频率: {item['frequency']}")