"""
测试优化版系统功能
"""
from multi_source_verifier import MultiSourceVerifier, DataSource, FetchStatus
from time_weighted_analyzer import TimeWeightedAnalyzer, DrawRecord
from event_driven_accuracy import AccuracyCalculator, EventBus, Event, EventType
from datetime import datetime, timedelta

# 生肖映射表
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


def test_time_weighted_analysis():
    """测试时间加权频率分析"""
    print("=" * 60)
    print("测试1: 时间加权频率分析")
    print("=" * 60)

    # 生成模拟历史数据
    now = datetime.now()
    draws = []
    for i in range(100):
        draw = DrawRecord(
            issue_number=f"{163-i}期",
            draw_date=now - timedelta(days=i*7),
            numbers=[1, 13, 25, 37, 49, 7, 19],
            zodiacs=['马', '马', '马', '马', '马', '鼠', '鼠']
        )
        draws.append(draw)

    analyzer = TimeWeightedAnalyzer(halflife_days=30)

    # 数字频率
    num_freq = analyzer.calc_number_frequency(draws)
    top12 = num_freq[:12]

    print(f"最近30天半衰期分析完成")
    print(f"Top 12热门数字: {[r.item for r in top12]}")

    # 生肖频率
    zodiac_freq = analyzer.calc_zodiac_frequency(draws)
    print(f"生肖频率排序:")
    for r in zodiac_freq:
        print(f"  {r.item}: 加权={r.weighted_frequency:.4f}")

    # 趋势对比
    comparison = analyzer.compare_simple_vs_weighted(draws)
    print(f"\n排名上升最多的数字(近期热门):")
    for item in comparison['top_rising'][:3]:
        print(f"  数字{item['number']}: {item['simple_rank']} -> {item['weighted_rank']}")

    return True


def test_accuracy_calculator():
    """测试准确率计算"""
    print("\n" + "=" * 60)
    print("测试2: 准确率计算")
    print("=" * 60)

    calculator = AccuracyCalculator(ZODIAC_MAPPING)

    # 模拟预测数据
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

    # 模拟实际开奖数据
    actual = {
        'numbers': [31, 15, 28, 2, 34, 47, 19],
        'zodiacs': ['鼠', '龙', '兔', '蛇', '鸡', '猴', '鼠']
    }

    # 计算准确率
    result = calculator.calculate('AM', '163期', prediction, actual)

    print(f"期号: {result.issue_number}")
    print(f"特肖6只命中率: {result.hit_rate_top6:.2f}%")
    print(f"三肖4组命中率: {result.hit_rate_triple4:.2f}%")
    print(f"热门12数字命中率: {result.hit_rate_top12:.2f}%")
    print(f"综合准确率: {result.accuracy_rate:.2f}%")

    return True


def test_event_bus():
    """测试事件总线"""
    print("\n" + "=" * 60)
    print("测试3: 事件总线")
    print("=" * 60)

    event_bus = EventBus()

    # 注册事件处理器
    received_events = []

    def handler(event):
        received_events.append(event)
        print(f"  收到事件: {event.event_type.value}")

    event_bus.subscribe(EventType.ACCURACY_CALCULATED, handler)

    # 发布事件
    test_event = Event(
        EventType.ACCURACY_CALCULATED,
        {'test': 'data', 'accuracy': 44.3}
    )
    event_bus.publish(test_event)

    if len(received_events) == 1:
        print("✓ 事件发布订阅正常工作")
        return True
    else:
        print("✗ 事件处理失败")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("优化版系统功能测试")
    print("=" * 60)

    results = []
    results.append(test_time_weighted_analysis())
    results.append(test_accuracy_calculator())
    results.append(test_event_bus())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)


if __name__ == "__main__":
    main()