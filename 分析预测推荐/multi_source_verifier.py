"""
多源数据校验模块
支持多源爬取、数据对比、一致性校验、自动选择
"""
import random
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FetchStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class DataSource:
    name: str
    url: str
    priority: int = 1  # 1=最高优先级


@dataclass
class FetchResult:
    source_name: str
    status: FetchStatus
    data: Optional[Dict]
    error: Optional[str] = None
    fetch_time: float = 0


class CircuitBreaker:
    """
    熔断器实现
    失败次数超过阈值后暂时停止请求，避免压垮数据源
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # 秒
        self.failures = {}
        self.last_failure_time = {}

    def is_open(self, source_name: str) -> bool:
        """检查熔断器是否打开"""
        if source_name not in self.failures:
            return False

        if self.failures[source_name] >= self.failure_threshold:
            # 检查是否超过恢复时间
            if time.time() - self.last_failure_time.get(source_name, 0) > self.recovery_timeout:
                # 可以尝试恢复
                self.failures[source_name] = 0
                return False
            return True
        return False

    def record_failure(self, source_name: str):
        self.failures[source_name] = self.failures.get(source_name, 0) + 1
        self.last_failure_time[source_name] = time.time()
        logger.warning(f"Circuit breaker: {source_name} failure count: {self.failures[source_name]}")

    def record_success(self, source_name: str):
        self.failures[source_name] = 0


@dataclass
class VerificationResult:
    is_consistent: bool
    preferred_source: Optional[str]
    all_data: List[FetchResult]
    discrepancy: Optional[str] = None


class MultiSourceVerifier:
    """
    多源数据校验器
    1. 并行从多个源获取数据
    2. 对比数据一致性
    3. 自动选择可信数据
    4. 不一致时告警
    """

    def __init__(self, sources: List[DataSource], db_pool=None):
        self.sources = {s.name: s for s in sources}
        self.circuit_breaker = CircuitBreaker()
        self.db_pool = db_pool

    def fetch_with_retry(self, source: DataSource, max_retries: int = 3, backoff_base: int = 2) -> FetchResult:
        """
        带指数退避的重试机制
        失败后等待: backoff_base^attempt + random 秒
        """
        for attempt in range(max_retries):
            # 检查熔断器
            if self.circuit_breaker.is_open(source.name):
                return FetchResult(
                    source_name=source.name,
                    status=FetchStatus.FAILED,
                    data=None,
                    error="Circuit breaker open"
                )

            start_time = time.time()
            try:
                # 实际爬取逻辑(需要集成Selenium/requests)
                data = self._do_fetch(source)

                self.circuit_breaker.record_success(source.name)

                return FetchResult(
                    source_name=source.name,
                    status=FetchStatus.SUCCESS,
                    data=data,
                    fetch_time=time.time() - start_time
                )

            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1} failed for {source.name}: {e}")
                self.circuit_breaker.record_failure(source.name)

                if attempt < max_retries - 1:
                    wait_time = backoff_base ** attempt + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    return FetchResult(
                        source_name=source.name,
                        status=FetchStatus.FAILED,
                        data=None,
                        error=str(e),
                        fetch_time=time.time() - start_time
                    )

        return FetchResult(
            source_name=source.name,
            status=FetchStatus.FAILED,
            data=None,
            error="Max retries exceeded"
        )

    def _do_fetch(self, source: DataSource) -> Dict:
        """
        实际爬取逻辑
        这里需要集成实际的爬虫代码
        """
        # TODO: 集成实际爬虫
        import requests
        response = requests.get(source.url, timeout=10)
        response.raise_for_status()
        return self._parse_response(response.text)

    def _parse_response(self, html: str) -> Dict:
        """解析HTML响应"""
        # TODO: 实现实际的HTML解析
        return {"numbers": [], "issue_number": "", "draw_date": ""}

    async def verify_and_fetch(self, issue_number: str) -> VerificationResult:
        """
        主校验流程
        1. 并行获取所有源数据
        2. 对比一致性
        3. 选择最佳数据
        """
        # 按优先级排序
        sorted_sources = sorted(self.sources.values(), key=lambda s: s.priority)

        # 并行获取(这里简化处理，实际用asyncio)
        results = []
        for source in sorted_sources:
            result = self.fetch_with_retry(source)
            results.append(result)

            # 如果成功获取且优先级最高，可以提前返回
            if result.status == FetchStatus.SUCCESS and source.priority == 1:
                break

        # 记录到数据库
        await self._save_verification_records(issue_number, results)

        # 数据一致性分析
        consistent_data = [r for r in results if r.status == FetchStatus.SUCCESS]

        if len(consistent_data) == 0:
            return VerificationResult(
                is_consistent=False,
                preferred_source=None,
                all_data=results,
                discrepancy="所有数据源均失败"
            )

        if len(consistent_data) == 1:
            return VerificationResult(
                is_consistent=True,
                preferred_source=consistent_data[0].source_name,
                all_data=results
            )

        # 多源数据对比
        first_data = consistent_data[0].data
        all_same = all(r.data == first_data for r in consistent_data)

        if all_same:
            return VerificationResult(
                is_consistent=True,
                preferred_source=consistent_data[0].source_name,
                all_data=results
            )
        else:
            # 数据不一致，告警并记录
            logger.error(f"Data inconsistency detected for {issue_number}")
            self._alert_inconsistency(issue_number, consistent_data)

            return VerificationResult(
                is_consistent=False,
                preferred_source=consistent_data[0].source_name,  # 选优先级最高的
                all_data=results,
                discrepancy=self._format_discrepancy(consistent_data)
            )

    async def _save_verification_records(self, issue_number: str, results: List[FetchResult]):
        """保存校验记录到数据库"""
        # TODO: 实现数据库保存
        pass

    def _alert_inconsistency(self, issue_number: str, results: List[FetchResult]):
        """数据不一致告警"""
        # TODO: 实现告警逻辑(企业微信/邮件等)
        logger.critical(f"DATA INCONSISTENCY: {issue_number} - {len(results)} sources with different data")

    def _format_discrepancy(self, results: List[FetchResult]) -> str:
        """格式化差异描述"""
        lines = []
        for r in results:
            lines.append(f"{r.source_name}: {r.data}")
        return " | ".join(lines)


# 使用示例
if __name__ == "__main__":
    sources = [
        DataSource(name="primary", url="https://2026kj.zkclhb.com:2025/am.html", priority=1),
        DataSource(name="backup1", url="https://backup1.example.com/am.html", priority=2),
        DataSource(name="backup2", url="https://backup2.example.com/am.html", priority=3),
    ]

    verifier = MultiSourceVerifier(sources)

    # 验证单期数据
    result = verifier.verify_and_fetch("163期")
    print(f"Consistent: {result.is_consistent}")
    print(f"Preferred source: {result.preferred_source}")
    print(f"Discrepancy: {result.discrepancy}")