"""
时间加权频率统计分析模块
相比简单频率统计，近期数据权重更高，更能反映趋势变化
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import math


@dataclass
class DrawRecord:
    """开奖记录"""
    issue_number: str
    draw_date: datetime
    numbers: List[int]  # 7个号码
    zodiacs: List[str]  # 对应生肖


@dataclass
class FrequencyResult:
    """频率统计结果"""
    item: any  # 数字或生肖
    weighted_count: float
    simple_count: int
    simple_frequency: float
    weighted_frequency: float


class TimeWeightedAnalyzer:
    """
    时间加权频率分析器

    算法说明:
    - 使用指数衰减作为权重: weight = 2^(-days_since / halflife)
    - halflife=30天表示每30天权重减半
    - 相比简单频率，更能反映近期趋势
    """

    def __init__(self, halflife_days: int = 30):
        """
        Args:
            halflife_days: 半衰期天数，默认30天
                           30天前的数据权重是当前的一半
        """
        self.halflife_days = halflife_days

    def calc_decay_weight(self, days_since: float) -> float:
        """
        计算时间衰减权重
        weight = 2^(-days_since / halflife)
        """
        return math.pow(2, -days_since / self.halflife_days)

    def calc_number_frequency(self, draws: List[DrawRecord], as_of_date: Optional[datetime] = None) -> List[FrequencyResult]:
        """
        计算数字频率(时间加权)

        Args:
            draws: 历史开奖记录列表(按日期升序)
            as_of_date: 计算截止日期，默认最新日期
        """
        if not draws:
            return []

        if as_of_date is None:
            as_of_date = draws[-1].draw_date

        # 计算每个数字的加权频率
        weighted_freq = {n: 0.0 for n in range(1, 50)}
        simple_freq = {n: 0 for n in range(1, 50)}

        for draw in draws:
            days_since = (as_of_date - draw.draw_date).days
            if days_since < 0:
                continue

            weight = self.calc_decay_weight(days_since)

            for num in draw.numbers:
                weighted_freq[num] += weight
                simple_freq[num] += 1

        # 计算总权重(用于归一化)
        total_weight = sum(self.calc_decay_weight((as_of_date - d.draw_date).days) for d in draws)
        total_simple = len(draws)

        results = []
        for num in range(1, 50):
            results.append(FrequencyResult(
                item=num,
                weighted_count=weighted_freq[num],
                simple_count=simple_freq[num],
                simple_frequency=simple_freq[num] / total_simple if total_simple > 0 else 0,
                weighted_frequency=weighted_freq[num] / total_weight if total_weight > 0 else 0
            ))

        # 按加权频率降序排列
        results.sort(key=lambda x: x.weighted_frequency, reverse=True)
        return results

    def calc_zodiac_frequency(self, draws: List[DrawRecord], as_of_date: Optional[datetime] = None) -> List[FrequencyResult]:
        """
        计算生肖频率(时间加权)
        """
        if not draws:
            return []

        if as_of_date is None:
            as_of_date = draws[-1].draw_date

        zodiac_list = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
        weighted_freq = {z: 0.0 for z in zodiac_list}
        simple_freq = {z: 0 for z in zodiac_list}

        for draw in draws:
            days_since = (as_of_date - draw.draw_date).days
            if days_since < 0:
                continue

            weight = self.calc_decay_weight(days_since)

            for zodiac in draw.zodiacs:
                if zodiac in weighted_freq:
                    weighted_freq[zodiac] += weight
                    simple_freq[zodiac] += 1

        total_weight = sum(self.calc_decay_weight((as_of_date - d.draw_date).days) for d in draws)
        total_simple = len(draws)

        results = []
        for zodiac in zodiac_list:
            results.append(FrequencyResult(
                item=zodiac,
                weighted_count=weighted_freq[zodiac],
                simple_count=simple_freq[zodiac],
                simple_frequency=simple_freq[zodiac] / total_simple if total_simple > 0 else 0,
                weighted_frequency=weighted_freq[zodiac] / total_weight if total_weight > 0 else 0
            ))

        results.sort(key=lambda x: x.weighted_frequency, reverse=True)
        return results

    def calc_triple_combo_frequency(self, draws: List[DrawRecord], as_of_date: Optional[datetime] = None) -> Dict[Tuple, float]:
        """
        计算三肖组合频率(时间加权)
        返回: {(生肖1, 生肖2, 生肖3): 加权频率}
        """
        from itertools import combinations
        from collections import defaultdict

        if not draws:
            return {}

        if as_of_date is None:
            as_of_date = draws[-1].draw_date

        combo_freq = defaultdict(float)

        for draw in draws:
            days_since = (as_of_date - draw.draw_date).days
            if days_since < 0:
                continue

            weight = self.calc_decay_weight(days_since)

            # 获取不重复的三肖组合
            unique_zodiacs = list(set(draw.zodiacs))
            for combo in combinations(sorted(unique_zodiacs), 3):
                combo_freq[combo] += weight

        return dict(combo_freq)

    def compare_simple_vs_weighted(self, draws: List[DrawRecord]) -> Dict:
        """
        对比简单频率 vs 时间加权频率的差异
        用于分析近期趋势变化
        """
        simple_num = self.calc_number_frequency(draws)
        weighted_num = self.calc_number_frequency(draws)

        # 只按简单频率排序
        simple_num.sort(key=lambda x: x.simple_frequency, reverse=True)
        weighted_num.sort(key=lambda x: x.weighted_frequency, reverse=True)

        # 计算排名变化
        rank_changes = []
        for i, (s, w) in enumerate(zip(simple_num, weighted_num)):
            simple_rank = i + 1
            weighted_rank = weighted_num.index(w) + 1
            rank_change = simple_rank - weighted_rank
            rank_changes.append({
                'number': s.item,
                'simple_rank': simple_rank,
                'weighted_rank': weighted_rank,
                'rank_change': rank_change,
                'simple_freq': s.simple_frequency,
                'weighted_freq': w.weighted_frequency,
                'trend': 'UP' if rank_change < 0 else 'DOWN' if rank_change > 0 else 'STABLE'
            })

        # 找出趋势变化最大的
        rank_changes.sort(key=lambda x: abs(x['rank_change']), reverse=True)

        return {
            'top_rising': [x for x in rank_changes if x['rank_change'] < 0][:5],  # 排名上升的
            'top_falling': [x for x in rank_changes if x['rank_change'] > 0][:5],  # 排名下降的
            'all_changes': rank_changes
        }


class AdaptiveWeightAnalyzer(TimeWeightedAnalyzer):
    """
    自适应权重分析器
    根据数据特征自动调整半衰期
    """

    def __init__(self, min_halflife: int = 7, max_halflife: int = 90):
        super().__init__(halflife_days=30)  # 默认30天
        self.min_halflife = min_halflife
        self.max_halflife = max_halflife

    def auto_tune_halflife(self, draws: List[DrawRecord]) -> int:
        """
        根据数据量自动调整半衰期
        数据量越大，半衰期可以设置得更长

        启发式规则:
        - < 30期: halflife = 7天
        - 30-100期: halflife = 14天
        - 100-200期: halflife = 30天
        - > 200期: halflife = 60天
        """
        n = len(draws)

        if n < 30:
            self.halflife_days = self.min_halflife
        elif n < 100:
            self.halflife_days = 14
        elif n < 200:
            self.halflife_days = 30
        else:
            self.halflife_days = 60

        self.halflife_days = min(max(self.halflife_days, self.min_halflife), self.max_halflife)

        return self.halflife_days


# 使用示例
if __name__ == "__main__":
    from datetime import datetime, timedelta

    # 模拟数据
    now = datetime.now()
    draws = []
    for i in range(100):
        draw = DrawRecord(
            issue_number=f"{163-i}期",
            draw_date=now - timedelta(days=i),
            numbers=[1, 13, 25, 37, 49, 7, 19],  # 简化
            zodiacs=['马', '鼠', '马', '鼠', '马', '鼠', '鼠']
        )
        draws.append(draw)

    # 时间加权分析
    analyzer = TimeWeightedAnalyzer(halflife_days=30)

    # 数字频率
    num_freq = analyzer.calc_number_frequency(draws)
    print("Top 10 热门数字 (时间加权):")
    for r in num_freq[:10]:
        print(f"  数字{r.item}: 加权频率={r.weighted_frequency:.4f}, 简单频率={r.simple_frequency:.4f}")

    # 生肖频率
    zodiac_freq = analyzer.calc_zodiac_frequency(draws)
    print("\n生肖频率排序:")
    for r in zodiac_freq:
        print(f"  {r.item}: 加权={r.weighted_frequency:.4f}, 简单={r.simple_frequency:.4f}")

    # 对比分析
    comparison = analyzer.compare_simple_vs_weighted(draws)
    print("\n排名上升最多的(近期热门):")
    for item in comparison['top_rising'][:3]:
        print(f"  数字{item['number']}: 简单排名{item['simple_rank']} -> 加权排名{item['weighted_rank']}")