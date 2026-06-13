"""
核心算法与预测模型
包含农历生肖计算、统计分析、预测推荐生成、准确率计算等核心算法
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from itertools import combinations

# 生肖列表
ZODIAC_LIST = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

# 生肖与数字映射（2026马年）
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

# 数字到生肖反向映射
NUM_TO_ZODIAC = {}
for zodiac, numbers in ZODIAC_NUMBER_MAP.items():
    for num in numbers:
        NUM_TO_ZODIAC[num] = zodiac

# 干支纪年与生肖映射
GANZHI_ZODIAC_MAP = {
    '甲子': '鼠', '乙丑': '牛', '丙寅': '虎', '丁卯': '兔', '戊辰': '龙', '己巳': '蛇',
    '庚午': '马', '辛未': '羊', '壬申': '猴', '癸酉': '鸡', '甲戌': '狗', '乙亥': '猪',
    '丙子': '鼠', '丁丑': '牛', '戊寅': '虎', '己卯': '兔', '庚辰': '龙', '辛巳': '蛇',
    '壬午': '马', '癸未': '羊', '甲申': '猴', '乙酉': '鸡', '丙戌': '狗', '丁亥': '猪',
    '戊子': '鼠', '己丑': '牛', '庚寅': '虎', '辛卯': '兔', '壬辰': '龙', '癸巳': '蛇',
    '甲午': '马', '乙未': '羊', '丙申': '猴', '丁酉': '鸡', '戊戌': '狗', '己亥': '猪',
    '庚子': '鼠', '辛丑': '牛', '壬寅': '虎', '癸卯': '兔', '甲辰': '龙', '乙巳': '蛇',
    '丙午': '马', '丁未': '羊', '戊申': '猴', '己酉': '鸡', '庚戌': '狗', '辛亥': '猪',
    '壬子': '鼠', '癸丑': '牛', '甲寅': '虎', '乙卯': '兔', '丙辰': '龙', '丁巳': '蛇',
    '戊午': '马', '己未': '羊', '庚申': '猴', '辛酉': '鸡', '壬戌': '狗', '癸亥': '猪'
}

# 十天干
TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# 十二地支
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 春节日期映射 (公历)
SPRING_FESTIVAL_DATES = {
    1977: (2, 18), 1978: (2, 7), 1979: (1, 28), 1980: (2, 16), 1981: (2, 5), 1982: (1, 25),
    1983: (2, 13), 1984: (2, 2), 1985: (2, 20), 1986: (2, 9), 1987: (1, 29), 1988: (2, 17),
    1989: (2, 6), 1990: (1, 27), 1991: (2, 15), 1992: (2, 4), 1993: (1, 23), 1994: (2, 10),
    1995: (1, 31), 1996: (2, 19), 1997: (2, 7), 1998: (1, 28), 1999: (2, 16), 2000: (2, 5),
    2001: (1, 24), 2002: (2, 12), 2003: (2, 1), 2004: (1, 22), 2005: (2, 9), 2006: (1, 29),
    2007: (2, 18), 2008: (2, 7), 2009: (1, 26), 2010: (2, 14), 2011: (2, 3), 2012: (1, 23),
    2013: (2, 10), 2014: (1, 31), 2015: (2, 19), 2016: (2, 8), 2017: (1, 28), 2018: (2, 16),
    2019: (2, 5), 2020: (1, 25), 2021: (2, 12), 2022: (2, 1), 2023: (1, 22), 2024: (2, 10),
    2025: (1, 29), 2026: (2, 17), 2027: (2, 6), 2028: (1, 26), 2029: (2, 13), 2030: (2, 3),
}


def get_ganzhi_by_year(year: int) -> str:
    """
    根据年份计算干支纪年
    
    Args:
        year: 农历年份
    
    Returns:
        干支纪年字符串（如"丙午"）
    """
    # 以1984年（甲子年）为基准
    base_year = 1984
    year_diff = year - base_year
    
    tiangan_index = year_diff % 10
    dizhi_index = year_diff % 12
    
    return TIANGAN[tiangan_index] + DIZHI[dizhi_index]


def get_lunar_year(draw_date: datetime) -> int:
    """
    根据公历日期计算农历年份
    
    Args:
        draw_date: 公历日期
    
    Returns:
        农历年份
    """
    year = draw_date.year
    spring_date = SPRING_FESTIVAL_DATES.get(year, (2, 10))
    
    if (draw_date.month, draw_date.day) >= spring_date:
        return year
    else:
        return year - 1


def get_lunar_zodiac_year(draw_date: datetime) -> Tuple[str, int]:
    """
    获取农历生肖年份
    
    Args:
        draw_date: 公历日期
    
    Returns:
        (生肖, 农历年份)
    """
    lunar_year = get_lunar_year(draw_date)
    ganzhi = get_ganzhi_by_year(lunar_year)
    zodiac = GANZHI_ZODIAC_MAP.get(ganzhi, '未知')
    
    return zodiac, lunar_year


def calc_number_frequency(db_path: str, source_id: str, use_full_history: bool = True, limit: int = 50) -> List[Tuple[int, int, float]]:
    """
    计算数字频率统计
    
    Args:
        db_path: 数据库路径
        source_id: 数据源标识(AM/HK)
        use_full_history: 是否使用全历史数据
        limit: 非全历史时的限制条数
    
    Returns:
        [(数字, 频率, 概率), ...]
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if use_full_history:
            cursor.execute(f"""
                SELECT numbers FROM lottery_data_{source_id.lower()} ORDER BY issue_number
            """)
        else:
            cursor.execute(f"""
                SELECT numbers FROM lottery_data_{source_id.lower()} ORDER BY issue_number DESC LIMIT ?
            """, (limit,))
        
        freq = [0] * 49
        for row in cursor.fetchall():
            try:
                numbers = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                for n in numbers:
                    if 1 <= n <= 49:
                        freq[n - 1] += 1
            except:
                continue
        
        total = sum(freq)
        if total == 0:
            return []
        
        probabilities = [f / total for f in freq]
        return list(zip(range(1, 50), freq, probabilities))
    
    finally:
        conn.close()


def calc_zodiac_freq_and_cooccurrence(db_path: str, source_id: str) -> Tuple[Dict[str, int], Dict[Tuple[str, str, str], int]]:
    """
    计算生肖频率及三生肖组合共现
    
    Args:
        db_path: 数据库路径
        source_id: 数据源标识(AM/HK)
    
    Returns:
        (生肖频率字典, 三生肖组合共现字典)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 生肖频率
        zodiac_freq = {z: 0 for z in ZODIAC_LIST}
        # 三生肖组合共现
        triple_combo = defaultdict(int)
        
        cursor.execute(f"""
            SELECT zodiacs FROM lottery_data_{source_id.lower()}
        """)
        
        for row in cursor.fetchall():
            try:
                zodiacs = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                # 统计生肖频率
                for z in zodiacs:
                    if z in zodiac_freq:
                        zodiac_freq[z] += 1
                # 生成所有3-组合
                unique_zodiacs = list(set(zodiacs))
                for combo in combinations(unique_zodiacs, 3):
                    triple_combo[tuple(sorted(combo))] += 1
            except:
                continue
        
        return dict(zodiac_freq), dict(triple_combo)
    
    finally:
        conn.close()


def calc_historical_accuracy_for_zodiac_as_top6(db_path: str, source_id: str, zodiac: str) -> float:
    """
    计算某生肖作为特肖推荐时的历史命中率
    
    Args:
        db_path: 数据库路径
        source_id: 数据源标识(AM/HK)
        zodiac: 生肖名称
    
    Returns:
        历史命中率(百分比)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取该生肖出现在特肖推荐中的期数
        cursor.execute(f"""
            SELECT p.issue_number, p.top6_zodiacs, l.zodiacs
            FROM predictions_{source_id.lower()} p
            LEFT JOIN lottery_data_{source_id.lower()} l ON p.issue_number = l.issue_number
            WHERE l.issue_number IS NOT NULL
        """)
        
        total_recommendations = 0
        total_hits = 0
        
        for row in cursor.fetchall():
            issue, top6_str, actual_zodiacs_str = row
            
            try:
                top6 = json.loads(top6_str) if isinstance(top6_str, str) else top6_str
                actual_zodiacs = json.loads(actual_zodiacs_str) if isinstance(actual_zodiacs_str, str) else actual_zodiacs_str
            except:
                continue
            
            # 检查该生肖是否在特肖推荐中
            zodiac_in_top6 = any(item.get('zodiac') == zodiac for item in top6)
            
            if zodiac_in_top6:
                total_recommendations += 1
                # 检查是否命中
                if zodiac in actual_zodiacs:
                    total_hits += 1
        
        if total_recommendations == 0:
            return 0.0
        
        return round((total_hits / total_recommendations) * 100, 2)
    
    finally:
        conn.close()


def generate_prediction(db_path: str, source_id: str) -> Dict:
    """
    生成预测推荐
    
    Args:
        db_path: 数据库路径
        source_id: 数据源标识(AM/HK)
    
    Returns:
        预测结果字典
    """
    # 获取全历史统计
    num_freq = calc_number_frequency(db_path, source_id, use_full_history=True)
    zodiac_freq, triple_combo = calc_zodiac_freq_and_cooccurrence(db_path, source_id)
    
    # 特肖6只：按生肖频率降序取前6，计算历史命中率
    top6_zodiacs = sorted(zodiac_freq.items(), key=lambda x: x[1], reverse=True)[:6]
    top6_result = []
    for z, freq in top6_zodiacs:
        hist_acc = calc_historical_accuracy_for_zodiac_as_top6(db_path, source_id, z)
        top6_result.append({
            "zodiac": z,
            "predicted_accuracy": hist_acc,
            "frequency": freq,
            "numbers": ZODIAC_NUMBER_MAP.get(z, [])
        })
    
    # 4组三肖：选取频率最高的4组，组间生肖不重叠
    sorted_triple = sorted(triple_combo.items(), key=lambda x: x[1], reverse=True)
    selected_groups = []
    used_zodiacs = set()
    
    for combo, cnt in sorted_triple:
        if len(selected_groups) >= 4:
            break
        if not set(combo) & used_zodiacs:
            selected_groups.append(combo)
            used_zodiacs.update(combo)
    
    # 如果不足4组，用剩余生肖补充
    if len(selected_groups) < 4:
        remaining_zodiacs = [z for z in ZODIAC_LIST if z not in used_zodiacs]
        while len(selected_groups) < 4 and len(remaining_zodiacs) >= 3:
            new_group = tuple(remaining_zodiacs[:3])
            selected_groups.append(new_group)
            used_zodiacs.update(new_group)
            remaining_zodiacs = remaining_zodiacs[3:]
    
    triple4_result = []
    for g in selected_groups:
        numbers = []
        for z in g:
            numbers.extend(ZODIAC_NUMBER_MAP.get(z, []))
        triple4_result.append({
            "group": list(g),
            "numbers": sorted(list(set(numbers))),
            "frequency": triple_combo.get(g, 0)
        })
    
    # 热门12数字：按数字频率降序取前12
    top12_numbers = sorted(num_freq, key=lambda x: x[1], reverse=True)[:12]
    hot_numbers = [{
        "number": n,
        "zodiac": NUM_TO_ZODIAC.get(n, ''),
        "frequency": f,
        "probability": round(p * 100, 2)
    } for n, f, p in top12_numbers]
    
    return {
        "top6": top6_result,
        "triple4": triple4_result,
        "hot12": hot_numbers,
        "generated_at": datetime.now().isoformat()
    }


def calculate_accuracy(prediction: Dict, actual_numbers: List[int], actual_zodiacs: List[str]) -> Dict:
    """
    计算准确率
    
    Args:
        prediction: 预测结果
        actual_numbers: 实际开出的号码
        actual_zodiacs: 实际开出的生肖
    
    Returns:
        准确率计算结果
    """
    # 特肖命中率 = 实际生肖与预测特肖6只的交集个数 / 6 × 100%
    predicted_zodiacs = [item['zodiac'] for item in prediction.get('top6', [])]
    top6_hits = sum(1 for z in actual_zodiacs if z in predicted_zodiacs)
    top6_rate = round((top6_hits / 6) * 100, 2)
    
    # 三肖命中率 = 实际生肖出现在预测三肖组中的组数 / 4 × 100%
    triple_groups = [set(group['group']) for group in prediction.get('triple4', [])]
    triple_hits = sum(1 for group in triple_groups if group & set(actual_zodiacs))
    triple_rate = round((triple_hits / 4) * 100, 2)
    
    # 数字命中率 = 实际数字与预测热门12数字的交集个数 / 7 × 100%
    predicted_numbers = [item['number'] for item in prediction.get('hot12', [])]
    num_hits = sum(1 for n in actual_numbers if n in predicted_numbers)
    num_rate = round((num_hits / 7) * 100, 2)
    
    # 综合加权准确率 = 特肖×0.6 + 三肖×0.3 + 数字×0.1
    combined_rate = round(top6_rate * 0.6 + triple_rate * 0.3 + num_rate * 0.1, 2)
    
    return {
        "hit_rate_top6": top6_rate,
        "hit_rate_triple4": triple_rate,
        "hit_rate_top12": num_rate,
        "accuracy_rate": combined_rate,
        "hit_status": {
            "top6_hits": top6_hits,
            "top6_total": 6,
            "triple4_hits": triple_hits,
            "triple4_total": 4,
            "top12_hits": num_hits,
            "top12_total": 7
        }
    }


# 使用示例
if __name__ == "__main__":
    db_path = '/Users/rs/AI/分析预测推荐/lottery.db'
    
    print("测试核心算法模块")
    print("=" * 60)
    
    # 测试农历生肖计算
    test_date = datetime(2026, 2, 16)  # 春节前一天
    zodiac, lunar_year = get_lunar_zodiac_year(test_date)
    print(f"日期 {test_date.date()} -> 农历年: {lunar_year} -> 生肖: {zodiac}")
    
    test_date2 = datetime(2026, 2, 17)  # 春节当天
    zodiac2, lunar_year2 = get_lunar_zodiac_year(test_date2)
    print(f"日期 {test_date2.date()} -> 农历年: {lunar_year2} -> 生肖: {zodiac2}")
    
    # 测试数字频率统计
    print("\n数字频率统计(前10):")
    num_freq = calc_number_frequency(db_path, 'AM')
    for n, f, p in num_freq[:10]:
        print(f"  {n}: 频率={f}, 概率={p:.4f}")
    
    # 测试生肖频率和组合共现
    zodiac_freq, triple_combo = calc_zodiac_freq_and_cooccurrence(db_path, 'AM')
    print("\n生肖频率:")
    for z, f in sorted(zodiac_freq.items(), key=lambda x: -x[1]):
        print(f"  {z}: {f}")
    
    print("\n三肖组合(前5):")
    for combo, cnt in sorted(triple_combo.items(), key=lambda x: -x[1])[:5]:
        print(f"  {combo}: {cnt}")
    
    # 测试预测生成
    print("\n生成预测:")
    prediction = generate_prediction(db_path, 'AM')
    
    print("\n特肖6只:")
    for i, item in enumerate(prediction['top6'], 1):
        print(f"  {i}. {item['zodiac']} (命中率: {item['predicted_accuracy']}%)")
    
    print("\n4组三肖:")
    for i, group in enumerate(prediction['triple4'], 1):
        print(f"  第{i}组: {group['group']} -> {group['numbers']}")
    
    print("\n热门12数字:")
    for i, item in enumerate(prediction['hot12'], 1):
        print(f"  {i}. {item['number']} ({item['zodiac']})")