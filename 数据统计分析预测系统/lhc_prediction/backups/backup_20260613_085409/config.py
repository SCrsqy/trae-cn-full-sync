import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(PROJECT_ROOT, 'lhc.db')

AM_URL = 'https://2026kj.zkclhb.com:2025/am.html#toubu13'
HK_URL = 'https://2026kj.zkclhb.com:2025/hk.html#toubu13'

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

ZODIAC_MAP = {
    '鼠': [7, 19, 31, 43],
    '牛': [8, 20, 32, 44],
    '虎': [9, 21, 33, 45],
    '兔': [10, 22, 34, 46],
    '龙': [11, 23, 35, 47],
    '蛇': [12, 24, 36, 48],
    '马': [1, 13, 25, 37, 49],
    '羊': [2, 14, 26, 38],
    '猴': [3, 15, 27, 39],
    '鸡': [4, 16, 28, 40],
    '狗': [5, 17, 29, 41],
    '猪': [6, 18, 30, 42]
}

ZODIAC_ORDER = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

SPRING_FESTIVAL_DATES = {
    2020: '2020-01-25',
    2021: '2021-02-12',
    2022: '2022-02-01',
    2023: '2023-01-22',
    2024: '2024-02-10',
    2025: '2025-01-29',
    2026: '2026-02-17',
    2027: '2027-02-06',
    2028: '2028-01-26',
    2029: '2029-02-13',
    2030: '2030-02-03'
}

ZODIAC_YEAR_MAP = {
    2020: '鼠',
    2021: '牛',
    2022: '虎',
    2023: '兔',
    2024: '龙',
    2025: '蛇',
    2026: '马',
    2027: '羊',
    2028: '猴',
    2029: '鸡',
    2030: '狗',
    2031: '猪'
}

def get_number_zodiac(number):
    for zodiac, numbers in ZODIAC_MAP.items():
        if number in numbers:
            return zodiac
    return None