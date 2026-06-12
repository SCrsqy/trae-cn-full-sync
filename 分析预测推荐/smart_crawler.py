"""
爬虫智能重试与熔断机制
实现指数退避、熔断保护、代理池、自动UA轮换
"""
import time
import random
import logging
from typing import Optional, Callable, Any, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import threading

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"  # 被反爬
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class RequestMetrics:
    """请求指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    blocks: int = 0
    total_latency: float = 0
    last_request_time: Optional[datetime] = None


class CircuitBreaker:
    """
    熔断器: 防止对故障源持续请求
    状态: CLOSED(正常) -> OPEN(熔断) -> HALF_OPEN(试探)
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> State:
        with self._lock:
            if self._state == self.State.OPEN:
                # 检查是否超时可以尝试恢复
                if self._last_failure_time and \
                   datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self._state = self.State.HALF_OPEN
                    self._success_count = 0
            return self._state

    def record_success(self):
        with self._lock:
            if self._state == self.State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    # 恢复成功，关闭熔断器
                    self._state = self.State.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker closed - recovery successful")
            else:
                self._failure_count = 0

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == self.State.HALF_OPEN:
                # 试探失败，重新打开
                self._state = self.State.OPEN
                logger.warning("Circuit breaker reopened - half-open probe failed")
            elif self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN
                logger.warning(f"Circuit breaker opened - {self._failure_count} consecutive failures")

    def is_available(self) -> bool:
        return self.state != self.State.OPEN


class ProxyPool:
    """
    代理池: 轮换使用多个代理，避免被封
    """

    def __init__(self, proxies: List[Dict[str, str]] = None):
        self.proxies = proxies or []
        self._current_index = 0
        self._lock = threading.Lock()
        self._failure_count: Dict[str, int] = {}

    def add_proxy(self, proxy: Dict[str, str]):
        self.proxies.append(proxy)

    def get_proxy(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None

        with self._lock:
            # 简单轮询，可改进为加权轮询
            proxy = self.proxies[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.proxies)
            return {'http': proxy.get('http'), 'https': proxy.get('https')}

    def record_proxy_failure(self, proxy: Dict[str, str]):
        """记录代理失败，可用于后续降权"""
        proxy_str = proxy.get('http', '')
        self._failure_count[proxy_str] = self._failure_count.get(proxy_str, 0) + 1

    def get_healthy_proxies(self) -> List[Dict[str, str]]:
        """获取健康代理(失败次数少于阈值)"""
        threshold = 5
        return [p for p in self.proxies
                if self._failure_count.get(p.get('http', ''), 0) < threshold]


class SmartCrawler:
    """
    智能爬虫: 集成重试、熔断、代理、UA轮换
    """

    # 常用User-Agent列表
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(
        self,
        max_retries: int = 3,
        base_backoff: float = 2.0,
        max_backoff: float = 60.0,
        timeout: float = 30.0,
        proxies: List[Dict[str, str]] = None
    ):
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.timeout = timeout

        self.circuit_breaker = CircuitBreaker()
        self.proxy_pool = ProxyPool(proxies)
        self.metrics = RequestMetrics()

        self._session: Optional[Any] = None
        self._lock = threading.Lock()

    def _get_session(self) -> Any:
        """获取或创建请求会话(带连接池)"""
        if requests is None:
            raise ImportError("requests library is required")

        if self._session is None:
            with self._lock:
                if self._session is None:
                    session = requests.Session()
                    # 配置重试适配器
                    retry_strategy = Retry(
                        total=0,  # 我们自己控制重试
                        backoff_factor=0
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    self._session = session
        return self._session

    def _get_headers(self) -> Dict[str, str]:
        """获取随机User-Agent"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def fetch(
        self,
        url: str,
        method: str = 'GET',
        parser: Optional[Callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        智能抓取

        Args:
            url: 目标URL
            method: 请求方法
            parser: 响应解析函数
            **kwargs: 其他requests参数

        Returns:
            {'status': RequestStatus, 'data': Any, 'error': str, 'latency': float}
        """
        start_time = time.time()

        # 检查熔断器
        if not self.circuit_breaker.is_available():
            logger.warning(f"Circuit breaker open for {url}")
            return {
                'status': RequestStatus.CIRCUIT_OPEN,
                'data': None,
                'error': 'Circuit breaker is open',
                'latency': time.time() - start_time
            }

        session = self._get_session()
        headers = self._get_headers()
        proxy = self.proxy_pool.get_proxy()

        for attempt in range(self.max_retries):
            try:
                # 请求
                request_kwargs = {
                    'url': url,
                    'method': method,
                    'headers': headers,
                    'timeout': self.timeout,
                    'proxies': proxy,
                    **kwargs
                }

                response = session.request(**request_kwargs)
                response.raise_for_status()

                # 检查是否被反爬
                if self._is_blocked(response):
                    self.circuit_breaker.record_failure()
                    logger.warning(f"Blocked by server: {url}")
                    return {
                        'status': RequestStatus.BLOCKED,
                        'data': None,
                        'error': 'Blocked by server',
                        'latency': time.time() - start_time
                    }

                # 解析响应
                data = response.text
                if parser:
                    data = parser(data)

                # 成功
                self.circuit_breaker.record_success()
                if proxy:
                    self.proxy_pool.get_healthy_proxies()  # 刷新健康代理

                self._update_metrics(True, time.time() - start_time)

                return {
                    'status': RequestStatus.SUCCESS,
                    'data': data,
                    'error': None,
                    'latency': time.time() - start_time,
                    'attempt': attempt + 1
                }

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}: {url}")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                    self._update_metrics(False, time.time() - start_time, timeout=True)
                    return {
                        'status': RequestStatus.TIMEOUT,
                        'data': None,
                        'error': 'Request timeout',
                        'latency': time.time() - start_time
                    }

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    self.circuit_breaker.record_failure()
                    self._update_metrics(False, time.time() - start_time)
                    return {
                        'status': RequestStatus.FAILED,
                        'data': None,
                        'error': str(e),
                        'latency': time.time() - start_time
                    }

            # 指数退避等待
            wait_time = min(self.base_backoff ** attempt + random.uniform(0, 1), self.max_backoff)
            time.sleep(wait_time)

        return {
            'status': RequestStatus.FAILED,
            'data': None,
            'error': 'Max retries exceeded',
            'latency': time.time() - start_time
        }

    def _is_blocked(self, response) -> bool:
        """检测是否被反爬"""
        # 检测常见反爬特征
        blocked_patterns = [
            '访问频率过快',
            '请输入验证码',
            '系统繁忙',
            '403 Forbidden',
            'captcha',
        ]
        content = response.text.lower()
        return any(p.lower() in content for p in blocked_patterns)

    def _update_metrics(self, success: bool, latency: float, timeout: bool = False):
        """更新请求指标"""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.last_request_time = datetime.now()
            self.metrics.total_latency += latency

            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
                if timeout:
                    self.metrics.timeouts += 1

    def get_metrics(self) -> RequestMetrics:
        """获取请求指标"""
        with self._lock:
            return RequestMetrics(
                total_requests=self.metrics.total_requests,
                successful_requests=self.metrics.successful_requests,
                failed_requests=self.metrics.failed_requests,
                timeouts=self.metrics.timeouts,
                blocks=self.metrics.blocks,
                total_latency=self.metrics.total_latency,
                last_request_time=self.metrics.last_request_time
            )

    def get_success_rate(self) -> float:
        """获取成功率"""
        with self._lock:
            if self.metrics.total_requests == 0:
                return 0.0
            return self.metrics.successful_requests / self.metrics.total_requests


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60
):
    """装饰器: 为函数添加熔断保护"""
    cb = CircuitBreaker(failure_threshold, recovery_timeout)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cb.is_available():
                raise RuntimeError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 创建爬虫实例
    crawler = SmartCrawler(
        max_retries=3,
        base_backoff=2.0,
        timeout=30.0
    )

    # 抓取数据
    result = crawler.fetch(
        url="https://2026kj.zkclhb.com:2025/am.html",
        parser=lambda x: x  # 简化，实际需要解析HTML
    )

    print(f"Status: {result['status']}")
    print(f"Latency: {result['latency']:.2f}s")
    print(f"Success rate: {crawler.get_success_rate():.2%}")

    # 获取熔断器状态
    print(f"Circuit breaker state: {crawler.circuit_breaker.state.value}")