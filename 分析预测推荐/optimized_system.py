"""
优化版系统主入口
整合所有新增模块:
- 多源数据校验
- 时间加权频率统计
- 智能爬虫
- 事件驱动准确率计算
- Prometheus监控
"""
from multi_source_verifier import MultiSourceVerifier, DataSource, FetchStatus
from time_weighted_analyzer import TimeWeightedAnalyzer, DrawRecord, AdaptiveWeightAnalyzer
from smart_crawler import SmartCrawler, CircuitBreaker
from event_driven_accuracy import (
    EventBus, Event, EventType, AccuracyCalculator, EventDrivenAccuracyService
)
from prometheus_metrics import create_metrics_app, record_crawl_success, record_prediction_accuracy
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


class OptimizedLotterySystem:
    """
    优化版彩票预测系统
    整合所有改进模块
    """

    def __init__(self):
        # 1. 数据源配置
        self.sources = [
            DataSource(name="primary", url="https://2026kj.zkclhb.com:2025/am.html", priority=1),
            DataSource(name="backup1", url="https://backup1.example.com/am.html", priority=2),
            DataSource(name="backup2", url="https://backup2.example.com/am.html", priority=3),
        ]
        self.verifier = MultiSourceVerifier(self.sources)

        # 2. 爬虫配置
        self.crawler = SmartCrawler(
            max_retries=3,
            base_backoff=2.0,
            timeout=30.0
        )

        # 3. 时间加权分析器
        self.analyzer = TimeWeightedAnalyzer(halflife_days=30)

        # 4. 事件总线
        self.event_bus = EventBus()

        # 5. 准确率计算器
        self.accuracy_calculator = AccuracyCalculator(ZODIAC_MAPPING)

        # 6. 事件驱动服务
        self.accuracy_service = EventDrivenAccuracyService(
            event_bus=self.event_bus,
            calculator=self.accuracy_calculator
        )

    def crawl_and_verify(self, issue_number: str):
        """多源爬取并校验"""
        result = self.verifier.verify_and_fetch(issue_number)

        if result.is_consistent:
            print(f"✓ Data verified from {result.preferred_source}")
            return result.all_data[0].data
        else:
            print(f"✗ Data inconsistency: {result.discrepancy}")
            # 仍然使用首选数据，但记录问题
            return result.all_data[0].data if result.all_data else None

    def analyze_with_time_weight(self, draws):
        """时间加权分析"""
        # 数字频率
        num_freq = self.analyzer.calc_number_frequency(draws)
        top_numbers = [r.item for r in num_freq[:12]]

        # 生肖频率
        zodiac_freq = self.analyzer.calc_zodiac_frequency(draws)
        top_zodiacs = [r.item for r in zodiac_freq[:6]]

        # 三肖组合
        combo_freq = self.analyzer.calc_triple_combo_frequency(draws)
        top_combos = sorted(combo_freq.items(), key=lambda x: -x[1])[:4]

        return {
            'top_numbers': top_numbers,
            'top_zodiacs': top_zodiacs,
            'top_combos': top_combos
        }

    def generate_prediction(self, analysis_result):
        """生成预测"""
        return {
            'top6_zodiacs': analysis_result['top_zodiacs'],
            'triple4_groups': [
                {'group': list(combo[0]), 'numbers': self._combo_to_numbers(combo[0])}
                for combo in analysis_result['top_combos']
            ],
            'top12_numbers': analysis_result['top_numbers']
        }

    def _combo_to_numbers(self, zodiac_combo):
        """三肖转换为数字"""
        numbers = []
        for zodiac in zodiac_combo:
            numbers.extend(ZODIAC_MAPPING.get(zodiac, []))
        return list(set(numbers))  # 去重

    def run_prediction_workflow(self, draws):
        """完整预测流程"""
        # 1. 时间加权分析
        analysis = self.analyze_with_time_weight(draws)

        # 2. 生成预测
        prediction = self.generate_prediction(analysis)

        return prediction

    def calculate_and_publish_accuracy(self, source_id, issue_number, prediction, actual):
        """计算准确率并发布事件"""
        result = self.accuracy_calculator.calculate(
            source_id, issue_number, prediction, actual
        )

        # 发布事件
        self.event_bus.publish(Event(
            EventType.ACCURACY_CALCULATED,
            result.to_dict()
        ))

        # 记录Prometheus指标
        record_prediction_accuracy(source_id, 'top6', result.hit_rate_top6)
        record_prediction_accuracy(source_id, 'combined', result.accuracy_rate)

        return result


def main():
    """主函数演示"""
    system = OptimizedLotterySystem()

    # 模拟历史数据
    now = datetime.now()
    draws = []
    for i in range(100):
        draw = DrawRecord(
            issue_number=f"{163-i}期",
            draw_date=now - timedelta(days=i*7),  # 每周一期
            numbers=[1, 13, 25, 37, 49, 7, 19],
            zodiacs=['马', '马', '马', '马', '马', '鼠', '鼠']
        )
        draws.append(draw)

    # 运行预测
    print("=== 优化版系统演示 ===")
    prediction = system.run_prediction_workflow(draws)
    print(f"Top6 Zodiacs: {prediction['top6_zodiacs']}")
    print(f"Top12 Numbers: {prediction['top12_numbers']}")

    # 计算准确率示例
    actual = {
        'numbers': [31, 15, 28, 2, 34, 47, 19],
        'zodiacs': ['马', '龙', '兔', '蛇', '鸡', '猴', '鼠']
    }

    accuracy_result = system.calculate_and_publish_accuracy(
        'AM', '163期', prediction, actual
    )

    print(f"\nAccuracy: {accuracy_result.accuracy_rate:.2f}%")

    # 启动metrics服务器
    print("\n=== 启动Metrics服务 ===")
    app = create_metrics_app()
    app.run(host='0.0.0.0', port=9090, debug=False)


if __name__ == "__main__":
    main()