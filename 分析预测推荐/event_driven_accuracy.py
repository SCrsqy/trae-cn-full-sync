"""
事件驱动准确率计算模块
替代定时轮询，新数据入库时立即触发计算并推送
"""
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import threading
from queue import Queue, Empty

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class EventType(Enum):
    LOTTERY_DATA_INSERTED = "lottery_data_inserted"
    PREDICTION_GENERATED = "prediction_generated"
    ACCURACY_CALCULATED = "accuracy_calculated"
    EXPORT_TRIGGERED = "export_triggered"


@dataclass
class AccuracyResult:
    """准确率计算结果"""
    source_id: str
    issue_number: str
    hit_rate_top6: float
    hit_rate_triple4: float
    hit_rate_top12: float
    accuracy_rate: float
    predicted_data: Dict
    actual_data: Dict
    calculated_at: datetime = None

    def __post_init__(self):
        if self.calculated_at is None:
            self.calculated_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'source_id': self.source_id,
            'issue_number': self.issue_number,
            'hit_rate_top6': self.hit_rate_top6,
            'hit_rate_triple4': self.hit_rate_triple4,
            'hit_rate_top12': self.hit_rate_top12,
            'accuracy_rate': self.accuracy_rate,
            'predicted_data': self.predicted_data,
            'actual_data': self.actual_data,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


class Event:
    """事件对象"""
    def __init__(self, event_type: EventType, payload: Dict, source: str = "system"):
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = datetime.now()
        self.event_id = f"{event_type.value}_{self.timestamp.timestamp()}"

    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type.value,
            'payload': self.payload,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'event_id': self.event_id
        }


class EventBus:
    """
    简单的事件总线
    支持事件发布订阅
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[callable]] = {et: [] for et in EventType}
        self._lock = threading.Lock()

    def subscribe(self, event_type: EventType, handler: callable):
        """订阅事件"""
        with self._lock:
            self._subscribers[event_type].append(handler)
            logger.info(f"Subscribed {handler.__name__} to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: callable):
        """取消订阅"""
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: Event):
        """发布事件"""
        with self._lock:
            handlers = self._subscribers[event.event_type].copy()

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler {handler.__name__} failed: {e}")

    def publish_async(self, event: Event):
        """异步发布事件(在后台线程执行)"""
        thread = threading.Thread(target=self.publish, args=(event,))
        thread.daemon = True
        thread.start()


class AccuracyCalculator:
    """
    准确率计算器
    计算预测与实际开奖的匹配程度
    """

    # 权重配置
    WEIGHT_TOP6 = 0.6
    WEIGHT_TRIPLE4 = 0.3
    WEIGHT_TOP12 = 0.1

    def __init__(self, zodiac_mapping: Dict[str, List[int]]):
        """
        Args:
            zodiac_mapping: 生肖到数字的映射
                           {'鼠': [7,19,31,43], '牛': [6,18,30,42], ...}
        """
        self.zodiac_mapping = zodiac_mapping
        self.number_to_zodiac: Dict[int, str] = {}
        for zodiac, numbers in zodiac_mapping.items():
            for num in numbers:
                self.number_to_zodiac[num] = zodiac

    def calculate(
        self,
        source_id: str,
        issue_number: str,
        prediction: Dict,
        actual_result: Dict
    ) -> AccuracyResult:
        """
        计算准确率

        Args:
            source_id: 'AM' or 'HK'
            issue_number: 期号
            prediction: 预测数据 {'top6_zodiacs': [...], 'triple4_groups': [...], 'top12_numbers': [...]}
            actual_result: 实际开奖数据 {'numbers': [...], 'zodiacs': [...]}
        """
        actual_numbers = set(actual_result.get('numbers', []))
        actual_zodiacs = set(actual_result.get('zodiacs', []))

        # 1. 特肖6只命中率
        pred_top6_zodiacs = prediction.get('top6_zodiacs', [])
        if isinstance(pred_top6_zodiacs, list) and len(pred_top6_zodiacs) > 0:
            # 支持两种格式: ['鼠', '龙'] 或 [{'zodiac': '鼠'}, ...]
            if isinstance(pred_top6_zodiacs[0], dict):
                pred_top6_zodiacs = [z.get('zodiac', '') for z in pred_top6_zodiacs]
        else:
            pred_top6_zodiacs = []

        hit6_count = len(set(pred_top6_zodiacs) & actual_zodiacs)
        hit_rate_top6 = (hit6_count / 6) * 100 if len(pred_top6_zodiacs) == 6 else 0

        # 2. 三肖4组命中率
        # 明确定义: 计算实际7个生肖中有多少个落在预测的4组三肖中
        pred_triple4_groups = prediction.get('triple4_groups', [])
        if isinstance(pred_triple4_groups, list) and len(pred_triple4_groups) > 0:
            if isinstance(pred_triple4_groups[0], dict):
                # 格式: [{'group': ['鼠', '龙', '猴'], 'numbers': [...]}, ...]
                pred_triple_sets = [set(g.get('group', [])) for g in pred_triple4_groups]
            else:
                # 格式: [['鼠', '龙', '猴'], ...]
                pred_triple_sets = [set(g) for g in pred_triple4_groups]
        else:
            pred_triple_sets = []

        # 计算落在预测组中的实际生肖数
        hit_triple_count = 0
        for zodiac in actual_zodiacs:
            for pred_set in pred_triple_sets:
                if zodiac in pred_set:
                    hit_triple_count += 1
                    break  # 每个生肖只计算一次

        hit_rate_triple4 = (hit_triple_count / 7) * 100

        # 3. 热门12数字命中率
        pred_top12 = prediction.get('top12_numbers', [])
        if isinstance(pred_top12, list) and len(pred_top12) > 0:
            if isinstance(pred_top12[0], dict):
                # 格式: [{'number': 31, 'zodiac': '鼠'}, ...]
                pred_top12_numbers = {n.get('number') for n in pred_top12 if n.get('number')}
            else:
                # 格式: [31, 7, 23, ...]
                pred_top12_numbers = set(pred_top12)
        else:
            pred_top12_numbers = set()

        hit12_count = len(actual_numbers & pred_top12_numbers)
        hit_rate_top12 = (hit12_count / 7) * 100 if len(pred_top12_numbers) > 0 else 0

        # 4. 综合加权准确率
        accuracy_rate = (
            hit_rate_top6 * self.WEIGHT_TOP6 +
            hit_rate_triple4 * self.WEIGHT_TRIPLE4 +
            hit_rate_top12 * self.WEIGHT_TOP12
        )

        return AccuracyResult(
            source_id=source_id,
            issue_number=issue_number,
            hit_rate_top6=hit_rate_top6,
            hit_rate_triple4=hit_rate_triple4,
            hit_rate_top12=hit_rate_top12,
            accuracy_rate=accuracy_rate,
            predicted_data=prediction,
            actual_data=actual_result
        )


class EventDrivenAccuracyService:
    """
    事件驱动的准确率计算服务
    替代定时轮询，数据入库立即计算
    """

    def __init__(
        self,
        event_bus: EventBus,
        calculator: AccuracyCalculator,
        redis_url: str = None
    ):
        self.event_bus = event_bus
        self.calculator = calculator
        self.redis_client = None

        if redis and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Connected to Redis for event pub/sub")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")

        # 订阅事件
        self.event_bus.subscribe(EventType.LOTTERY_DATA_INSERTED, self._on_lottery_data_inserted)
        self.event_bus.subscribe(EventType.PREDICTION_GENERATED, self._on_prediction_generated)

    def _on_lottery_data_inserted(self, event: Event):
        """新数据入库事件处理"""
        payload = event.payload
        source_id = payload.get('source_id')
        issue_number = payload.get('issue_number')

        logger.info(f"Processing accuracy calculation for {source_id} {issue_number}")

        # 获取对应的预测数据(需要从数据库查询)
        prediction = self._get_prediction(source_id, issue_number)
        if not prediction:
            logger.warning(f"No prediction found for {source_id} {issue_number}")
            return

        # 获取实际开奖数据
        actual_result = payload.get('actual_result')
        if not actual_result:
            actual_result = self._get_actual_result(source_id, issue_number)

        if not actual_result:
            logger.warning(f"No actual result for {source_id} {issue_number}")
            return

        # 计算准确率
        result = self.calculator.calculate(source_id, issue_number, prediction, actual_result)

        # 发布准确率计算完成事件
        self.event_bus.publish(Event(
            EventType.ACCURACY_CALCULATED,
            result.to_dict()
        ))

        # 推送到Redis供WebSocket使用
        if self.redis_client:
            self._push_to_redis(result)

    def _on_prediction_generated(self, event: Event):
        """新预测生成事件处理"""
        # 可选: 生成预测时预先准备计算所需数据
        pass

    def _get_prediction(self, source_id: str, issue_number: str) -> Optional[Dict]:
        """从数据库获取预测数据"""
        # TODO: 实现数据库查询
        return None

    def _get_actual_result(self, source_id: str, issue_number: str) -> Optional[Dict]:
        """从数据库获取实际开奖数据"""
        # TODO: 实现数据库查询
        return None

    def _push_to_redis(self, result: AccuracyResult):
        """推送结果到Redis供WebSocket使用"""
        try:
            channel = f"accuracy:{result.source_id}"
            self.redis_client.publish(channel, json.dumps(result.to_dict()))
        except Exception as e:
            logger.error(f"Failed to push to Redis: {e}")


# 独立触发器(兼容原有PostgreSQL触发器方案)
class AccuracyTrigger:
    """
    独立准确率触发器
    可作为PostgreSQL触发器的替代或补充
    """

    def __init__(self, calculator: AccuracyCalculator, db_pool):
        self.calculator = calculator
        self.db_pool = db_pool
        self._queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None

    def trigger(self, source_id: str, issue_number: str):
        """触发准确率计算"""
        self._queue.put((source_id, issue_number))
        self._ensure_worker()

    def _ensure_worker(self):
        """确保后台工作线程运行"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._worker_thread.start()

    def _process_queue(self):
        """后台处理队列"""
        while True:
            try:
                source_id, issue_number = self._queue.get(timeout=1)
                self._calculate_and_update(source_id, issue_number)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing accuracy calculation: {e}")

    def _calculate_and_update(self, source_id: str, issue_number: str):
        """计算并更新数据库"""
        # TODO: 实现数据库操作
        pass


# 使用示例
if __name__ == "__main__":
    # 生肖映射
    zodiac_mapping = {
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

    # 创建组件
    calculator = AccuracyCalculator(zodiac_mapping)
    event_bus = EventBus()

    # 模拟数据
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
        'zodiacs': ['马', '龙', '兔', '蛇', '鸡', '猴', '鼠']
    }

    # 计算
    result = calculator.calculate('AM', '163期', prediction, actual)

    print("=== 准确率计算结果 ===")
    print(f"期号: {result.issue_number}")
    print(f"特肖6只命中率: {result.hit_rate_top6:.2f}%")
    print(f"三肖4组命中率: {result.hit_rate_triple4:.2f}%")
    print(f"热门12数字命中率: {result.hit_rate_top12:.2f}%")
    print(f"综合准确率: {result.accuracy_rate:.2f}%")