from zhdate import ZhDate
from datetime import datetime
from config import ZODIAC_MAP

def get_zodiac_by_date(date_str):
    """
    根据公历日期获取生肖，严格遵循春节前后生肖差1的规则
    :param date_str: 公历日期字符串，格式如 '2024-02-10'
    :return: 生肖名称（鼠、牛、虎、兔、龙、蛇、马、羊、猴、鸡、狗、猪）
    """
    try:
        gregorian_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        lunar = ZhDate.from_datetime(gregorian_date)
        
        spring_festival = ZhDate(lunar.lunar_year, 1, 1).to_datetime()
        
        if gregorian_date < spring_festival:
            zodiac_year = lunar.lunar_year - 1
        else:
            zodiac_year = lunar.lunar_year
        
        zodiacs = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        
        return zodiacs[(zodiac_year - 4) % 12]
    
    except Exception as e:
        print(f'生肖判定错误: {e}')
        return None

def get_zodiac_by_number(number):
    """
    根据号码获取对应的生肖
    :param number: 号码（1-49）
    :return: 生肖名称
    """
    for zodiac, numbers in ZODIAC_MAP.items():
        if number in numbers:
            return zodiac
    return None

def get_numbers_by_zodiac(zodiac):
    """
    根据生肖获取对应的所有号码
    :param zodiac: 生肖名称
    :return: 号码列表
    """
    return ZODIAC_MAP.get(zodiac, [])

def get_chinese_year(date_str):
    """
    根据公历日期获取农历年份
    :param date_str: 公历日期字符串
    :return: 农历年份
    """
    try:
        gregorian_date = datetime.strptime(date_str, '%Y-%m-%d')
        lunar = ZhDate.from_datetime(gregorian_date)
        spring_festival = ZhDate(lunar.lunar_year, 1, 1).to_datetime()
        
        if gregorian_date < spring_festival:
            return lunar.lunar_year - 1
        else:
            return lunar.lunar_year
    except Exception as e:
        print(f'农历年份计算错误: {e}')
        return None

if __name__ == '__main__':
    test_dates = [
        '2024-02-09',   # 龙年春节前，属兔
        '2024-02-10',   # 龙年春节，属龙
        '2024-02-11',   # 龙年春节后，属龙
        '2023-01-21',   # 兔年春节前，属虎
        '2023-01-22',   # 兔年春节，属兔
        '2025-01-28',   # 蛇年春节前，属龙
        '2025-01-29',   # 蛇年春节，属蛇
        '2020-01-24',   # 鼠年春节前，属猪
        '2020-01-25',   # 鼠年春节，属鼠
    ]
    
    print('=== 生肖判定测试 ===')
    for date in test_dates:
        zodiac = get_zodiac_by_date(date)
        chinese_year = get_chinese_year(date)
        print(f'{date} -> 农历{chinese_year}年 -> 生肖: {zodiac}')
    
    print('\n=== 号码生肖测试 ===')
    test_numbers = [1, 7, 13, 25, 37, 49]
    for num in test_numbers:
        print(f'{num} -> {get_zodiac_by_number(num)}')