"""
端到端集成测试
验证完整的爬取、分析、预测、准确率计算流程
"""
import json
import sqlite3
from datetime import datetime, timedelta

# 导入所有模块
from multi_source_verifier import MultiSourceVerifier, DataSource
from time_weighted_analyzer import TimeWeightedAnalyzer, DrawRecord
from event_driven_accuracy import AccuracyCalculator, EventBus, Event, EventType
from anti_crawler import AdvancedCrawler, CrawlConfig, AntiDetectLevel

# 生肖映射
ZODIAC_MAPPING = {
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


def test_database_operations():
    """测试数据库操作"""
    print("=" * 60)
    print("测试1: 数据库操作")
    print("=" * 60)

    conn = sqlite3.connect('/Users/rs/AI/分析预测推荐/lottery.db')
    cursor = conn.cursor()

    try:
        # 查询数据
        cursor.execute("SELECT * FROM lottery_data_am WHERE issue_number = '163期'")
        row = cursor.fetchone()
        if row:
            print(f"✓ 查询成功: {row[1]}")
        else:
            print("✗ 查询失败")
            return False

        # 插入测试数据
        test_data = {
            'issue_number': '164期',
            'draw_date': '2026-06-19',
            'draw_date_lunar': '甲辰年五月十四',
            'lunar_year': 2024,
            'lunar_zodiac_year': '龙',
            'numbers': '[1, 13, 25, 37, 49, 7, 19]',
            'zodiacs': '["马", "马", "马", "马", "马", "鼠", "鼠"]'
        }

        cursor.execute("""
            INSERT OR IGNORE INTO lottery_data_am 
            (issue_number, draw_date, draw_date_lunar, lunar_year, lunar_zodiac_year, numbers, zodiacs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            test_data['issue_number'],
            test_data['draw_date'],
            test_data['draw_date_lunar'],
            test_data['lunar_year'],
            test_data['lunar_zodiac_year'],
            test_data['numbers'],
            test_data['zodiacs']
        ))
        conn.commit()
        print("✓ 插入成功")

        # 验证插入
        cursor.execute("SELECT COUNT(*) FROM lottery_data_am")
        count = cursor.fetchone()[0]
        print(f"✓ 当前记录数: {count}")

        return True

    finally:
        conn.close()


def test_time_weighted_analysis():
    """测试时间加权分析"""
    print("\n" + "=" * 60)
    print("测试2: 时间加权频率分析")
    print("=" * 60)

    # 生成模拟数据
    now = datetime.now()
    draws = []
    for i in range(50):
        draw = DrawRecord(
            issue_number=f"{163-i}期",
            draw_date=now - timedelta(days=i*7),
            numbers=[1, 13, 25, 37, 49, 7, 19],
            zodiacs=['马', '马', '马', '马', '马', '鼠', '鼠']
        )
        draws.append(draw)

    analyzer = TimeWeightedAnalyzer(halflife_days=30)
    num_freq = analyzer.calc_number_frequency(draws)
    zodiac_freq = analyzer.calc_zodiac_frequency(draws)

    print(f"✓ 分析完成")
    print(f"  Top 5数字: {[r.item for r in num_freq[:5]]}")
    print(f"  Top 3生肖: {[r.item for r in zodiac_freq[:3]]}")

    return True


def test_accuracy_calculation():
    """测试准确率计算"""
    print("\n" + "=" * 60)
    print("测试3: 准确率计算")
    print("=" * 60)

    calculator = AccuracyCalculator(ZODIAC_MAPPING)

    prediction = {
        'top6_zodiacs': ['鼠', '龙', '猴', '虎', '牛', '兔'],
        'triple4_groups': [
            {'group': ['鼠', '龙', '猴'], 'numbers': [7, 19, 31, 3, 15, 27, 11, 23, 35]},
            {'group': ['虎', '牛', '兔'], 'numbers': [5, 17, 29, 6, 18, 30, 4, 16, 28]},
            {'group': ['蛇', '马', '羊'], 'numbers': [2, 14, 26, 1, 13, 25, 12, 24, 36]},
            {'group': ['鸡', '狗', '猪'], 'numbers': [10, 22, 34, 9, 21, 33, 8, 20, 32]}
        ],
        'top12_numbers': [31, 7, 23, 15, 42, 18, 11, 36, 44, 29, 3, 38]
    }

    actual = {
        'numbers': [31, 15, 28, 2, 34, 47, 19],
        'zodiacs': ['鼠', '龙', '兔', '蛇', '鸡', '猴', '鼠']
    }

    result = calculator.calculate('AM', '163期', prediction, actual)

    print(f"✓ 计算完成")
    print(f"  特肖6只命中率: {result.hit_rate_top6:.2f}%")
    print(f"  三肖4组命中率: {result.hit_rate_triple4:.2f}%")
    print(f"  热门12数字命中率: {result.hit_rate_top12:.2f}%")
    print(f"  综合准确率: {result.accuracy_rate:.2f}%")

    return True


def test_event_bus():
    """测试事件总线"""
    print("\n" + "=" * 60)
    print("测试4: 事件总线")
    print("=" * 60)

    event_bus = EventBus()
    received_events = []

    def handler(event):
        received_events.append(event)
        print(f"  收到事件: {event.event_type.value}")

    event_bus.subscribe(EventType.ACCURACY_CALCULATED, handler)

    test_event = Event(
        EventType.ACCURACY_CALCULATED,
        {'issue_number': '163期', 'accuracy': 44.3}
    )
    event_bus.publish(test_event)

    if len(received_events) == 1:
        print("✓ 事件发布订阅正常")
        return True
    else:
        print("✗ 事件处理失败")
        return False


def test_crawler():
    """测试增强版爬虫"""
    print("\n" + "=" * 60)
    print("测试5: 增强版爬虫")
    print("=" * 60)

    config = CrawlConfig(
        max_retries=2,
        base_delay=1.0,
        anti_detect_level=AntiDetectLevel.ADVANCED
    )
    crawler = AdvancedCrawler(config)

    try:
        response = crawler.get("https://httpbin.org/headers")
        data = response.json()
        print(f"✓ 请求成功")
        print(f"  User-Agent: {data['headers']['User-Agent'][:50]}...")
        return True
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def main():
    """运行所有集成测试"""
    print("=" * 60)
    print("端到端集成测试")
    print("=" * 60)

    results = []
    results.append(test_database_operations())
    results.append(test_time_weighted_analysis())
    results.append(test_accuracy_calculation())
    results.append(test_event_bus())
    results.append(test_crawler())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有集成测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)


if __name__ == "__main__":
    main()