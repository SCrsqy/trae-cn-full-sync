"""
农历日期转换与生肖计算模块
支持公历日期到农历日期的转换
遵循春节前后生肖相差1的规则
"""
from datetime import datetime
from typing import Tuple, Optional, Dict

# 春节日期映射表 (公历)
# 格式: 年份 -> (春节月份, 春节日期)
SPRING_FESTIVAL_DATES = {
    1977: (2, 18),
    1978: (2, 7),
    1979: (1, 28),
    1980: (2, 16),
    1981: (2, 5),
    1982: (1, 25),
    1983: (2, 13),
    1984: (2, 2),
    1985: (2, 20),
    1986: (2, 9),
    1987: (1, 29),
    1988: (2, 17),
    1989: (2, 6),
    1990: (1, 27),
    1991: (2, 15),
    1992: (2, 4),
    1993: (1, 23),
    1994: (2, 10),
    1995: (1, 31),
    1996: (2, 19),
    1997: (2, 7),
    1998: (1, 28),
    1999: (2, 16),
    2000: (2, 5),
    2001: (1, 24),
    2002: (2, 12),
    2003: (2, 1),
    2004: (1, 22),
    2005: (2, 9),
    2006: (1, 29),
    2007: (2, 18),
    2008: (2, 7),
    2009: (1, 26),
    2010: (2, 14),
    2011: (2, 3),
    2012: (1, 23),
    2013: (2, 10),
    2014: (1, 31),
    2015: (2, 19),
    2016: (2, 8),
    2017: (1, 28),
    2018: (2, 16),
    2019: (2, 5),
    2020: (1, 25),
    2021: (2, 12),
    2022: (2, 1),
    2023: (1, 22),
    2024: (2, 10),
    2025: (1, 29),
    2026: (2, 17),
    2027: (2, 6),
    2028: (1, 26),
    2029: (2, 13),
    2030: (2, 3),
}

# 生肖顺序 (从鼠开始)
ZODIAC_ORDER = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

# 生肖对应的数字 (按用户提供的基准表)
# 2026年是马年，所以马年对应的数字为: 1, 13, 25, 37, 49
ZODIAC_NUMBERS_2026 = {
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


def get_lunar_year(year: int, month: int, day: int) -> int:
    """
    根据公历日期计算农历年份
    
    规则：春节前属于上一农历年，春节后属于当前农历年
    
    Args:
        year: 公历年份
        month: 公历月份
        day: 公历日期
    
    Returns:
        农历年份
    """
    # 获取当年春节日期
    spring_date = SPRING_FESTIVAL_DATES.get(year)
    
    if spring_date is None:
        # 如果没有配置，使用默认规则
        # 默认春节在2月10日左右
        if (month, day) >= (2, 10):
            return year
        else:
            return year - 1
    
    spring_month, spring_day = spring_date
    
    # 比较日期
    if (month > spring_month) or (month == spring_month and day >= spring_day):
        return year
    else:
        return year - 1


def get_zodiac_by_lunar_year(lunar_year: int) -> str:
    """
    根据农历年份获取生肖
    
    Args:
        lunar_year: 农历年份
    
    Returns:
        生肖名称
    """
    # 2026年是马年，作为基准
    base_year = 2026
    base_zodiac_index = ZODIAC_ORDER.index('马')
    
    # 计算年份差
    year_diff = lunar_year - base_year
    
    # 获取生肖索引
    zodiac_index = (base_zodiac_index + year_diff) % 12
    
    return ZODIAC_ORDER[zodiac_index]


def get_zodiac_for_date(year: int, month: int, day: int) -> str:
    """
    根据公历日期获取生肖
    
    Args:
        year: 公历年份
        month: 公历月份
        day: 公历日期
    
    Returns:
        生肖名称
    """
    lunar_year = get_lunar_year(year, month, day)
    return get_zodiac_by_lunar_year(lunar_year)


def get_zodiac_for_datetime(date: datetime) -> str:
    """
    根据datetime对象获取生肖
    
    Args:
        date: datetime对象
    
    Returns:
        生肖名称
    """
    return get_zodiac_for_date(date.year, date.month, date.day)


def get_zodiac_for_number(number: int, year: int = 2026) -> str:
    """
    根据号码获取生肖（基于2026年映射）
    
    Args:
        number: 号码(1-49)
        year: 年份（用于确定生肖映射，默认2026马年）
    
    Returns:
        生肖名称，如果号码无效返回空字符串
    """
    if number < 1 or number > 49:
        return ''
    
    # 获取当前年份对应的生肖映射
    # 由于生肖映射每12年循环一次，我们需要根据年份调整
    base_year = 2026
    year_diff = year - base_year
    zodiac_index_shift = year_diff % 12
    
    # 找到包含该号码的生肖
    for zodiac, numbers in ZODIAC_NUMBERS_2026.items():
        if number in numbers:
            # 根据年份调整生肖
            original_index = ZODIAC_ORDER.index(zodiac)
            new_index = (original_index - zodiac_index_shift) % 12
            return ZODIAC_ORDER[new_index]
    
    return ''


def get_numbers_for_zodiac(zodiac: str, year: int = 2026) -> list:
    """
    根据生肖获取对应的号码（基于2026年映射）
    
    Args:
        zodiac: 生肖名称
        year: 年份（用于确定生肖映射，默认2026马年）
    
    Returns:
        号码列表
    """
    base_year = 2026
    year_diff = year - base_year
    zodiac_index_shift = year_diff % 12
    
    # 找到目标生肖在当前年份对应的原始生肖
    target_index = ZODIAC_ORDER.index(zodiac)
    original_index = (target_index + zodiac_index_shift) % 12
    original_zodiac = ZODIAC_ORDER[original_index]
    
    return ZODIAC_NUMBERS_2026.get(original_zodiac, [])


def get_lunar_year_info(date: datetime) -> dict:
    """
    获取日期的农历年信息
    
    Args:
        date: datetime对象
    
    Returns:
        包含农历年、生肖、春节日期的字典
    """
    lunar_year = get_lunar_year(date.year, date.month, date.day)
    zodiac = get_zodiac_by_lunar_year(lunar_year)
    
    spring_date = SPRING_FESTIVAL_DATES.get(date.year)
    if spring_date:
        spring_month, spring_day = spring_date
        spring_date_str = f"{date.year}-{spring_month:02d}-{spring_day:02d}"
    else:
        spring_date_str = "未知"
    
    return {
        'lunar_year': lunar_year,
        'zodiac': zodiac,
        'spring_festival': spring_date_str,
        'is_before_spring': (date.month, date.day) < spring_date if spring_date else False
    }


# 全局映射函数（保持向后兼容）
def number_to_zodiac(number: int) -> str:
    """
    号码转生肖（默认使用2026年映射）
    """
    return get_zodiac_for_number(number, 2026)


def zodiac_to_numbers(zodiac: str) -> list:
    """
    生肖转号码（默认使用2026年映射）
    """
    return get_numbers_for_zodiac(zodiac, 2026)


# 测试
if __name__ == "__main__":
    print("测试农历生肖计算模块")
    print("=" * 50)
    
    # 测试春节前后生肖变化
    test_dates = [
        (2026, 2, 16),  # 春节前一天
        (2026, 2, 17),  # 春节当天
        (2026, 2, 18),  # 春节后一天
        (2025, 1, 28),  # 2025年春节前
        (2025, 1, 29),  # 2025年春节
    ]
    
    for year, month, day in test_dates:
        zodiac = get_zodiac_for_date(year, month, day)
        lunar_year = get_lunar_year(year, month, day)
        print(f"{year}-{month:02d}-{day:02d} -> 农历年: {lunar_year} -> 生肖: {zodiac}")
    
    print("\n生肖号码映射测试:")
    for zodiac in ZODIAC_ORDER:
        numbers = zodiac_to_numbers(zodiac)
        print(f"{zodiac}: {numbers}")