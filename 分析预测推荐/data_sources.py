"""
数据源配置
澳门(M)和香港(HK)的历史数据抓取
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """数据源配置"""
    name: str          # 名称: 澳门/香港
    code: str          # 代码: AM/HK
    url: str           # 抓取URL
    enabled: bool = True


# 数据源列表
DATA_SOURCES = [
    DataSource(
        name="澳门",
        code="AM",
        url="https://2026kj.zkclhb.com:2025/am.html#toubu13"
    ),
    DataSource(
        name="香港",
        code="HK",
        url="https://2026kj.zkclhb.com:2025/hk.html#toubu13"
    ),
]


class DataSourceManager:
    """
    数据源管理器
    支持多数据源配置和切换
    """

    def __init__(self):
        self.sources = {s.code: s for s in DATA_SOURCES}
        self.active_source = 'AM'  # 默认澳门

    def get_source(self, code: str) -> Optional[DataSource]:
        """获取指定数据源"""
        return self.sources.get(code)

    def get_active_source(self) -> DataSource:
        """获取当前活跃数据源"""
        return self.sources[self.active_source]

    def get_all_sources(self) -> List[DataSource]:
        """获取所有数据源"""
        return list(self.sources.values())

    def set_active_source(self, code: str):
        """设置活跃数据源"""
        if code in self.sources:
            self.active_source = code
            logger.info(f"切换到数据源: {self.sources[code].name}")

    def is_enabled(self, code: str) -> bool:
        """检查数据源是否启用"""
        source = self.sources.get(code)
        return source.enabled if source else False

    def get_source_info(self) -> Dict:
        """获取数据源信息"""
        return {
            'all_sources': [
                {'code': s.code, 'name': s.name, 'url': s.url, 'enabled': s.enabled}
                for s in self.sources.values()
            ],
            'active_source': self.active_source
        }


# 全局实例
source_manager = DataSourceManager()


# HTML解析器基类
class BaseParser:
    """解析器基类"""

    def parse(self, html: str) -> List[Dict]:
        """解析HTML，返回开奖数据列表"""
        raise NotImplementedError


class AMHTMLParser(BaseParser):
    """澳门数据HTML解析器"""

    def parse(self, html: str) -> List[Dict]:
        """解析澳门页面HTML"""
        import re
        import json

        results = []

        # 尝试多种匹配模式
        patterns = [
            # 模式1: 期号和开奖数据
            r'<td[^>]*>(\d+)期</td>.*?<td[^>]*>([\d,\s]+)</td>',
            # 模式2: JSON格式
            r'"issue"\s*:\s*"(\d+)期"[^}]*"numbers"\s*:\s*\[([^\]]+)\]',
            # 模式3: 简单表格
            r'<tr[^>]*>.*?(\d+)期.*?(\d+(?:\s*,?\s*\d+){6,7}).*?</tr>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    issue = match[0].strip()
                    numbers_str = match[1].strip()

                    # 提取数字
                    numbers = [int(n) for n in re.findall(r'\d+', numbers_str) if 1 <= int(n) <= 49]
                    if len(numbers) >= 7:
                        numbers = numbers[:7]

                        results.append({
                            'issue_number': f"{issue}期",
                            'numbers': numbers,
                            'source': 'AM'
                        })
                except Exception:
                    continue

            if results:
                break

        return results


class HKHTMLParser(BaseParser):
    """香港数据HTML解析器"""

    def parse(self, html: str) -> List[Dict]:
        """解析香港页面HTML"""
        # 香港可能使用不同的页面结构
        import re

        results = []

        # 类似澳门的解析模式
        patterns = [
            r'<td[^>]*>(\d+)期</td>.*?<td[^>]*>([\d,\s]+)</td>',
            r'"issue"\s*:\s*"(\d+)期"[^}]*"numbers"\s*:\s*\[([^\]]+)\]',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    issue = match[0].strip()
                    numbers_str = match[1].strip()

                    numbers = [int(n) for n in re.findall(r'\d+', numbers_str) if 1 <= int(n) <= 49]
                    if len(numbers) >= 7:
                        numbers = numbers[:7]

                        results.append({
                            'issue_number': f"{issue}期",
                            'numbers': numbers,
                            'source': 'HK'
                        })
                except Exception:
                    continue

            if results:
                break

        return results


class DataSourceCrawler:
    """
    数据源爬虫
    从指定URL抓取数据
    """

    def __init__(self, parser: BaseParser = None):
        self.parser = parser or AMHTMLParser()
        self.crawler = None  # 将使用anti_crawler模块

    def set_parser(self, parser: BaseParser):
        """设置解析器"""
        self.parser = parser

    def crawl(self, url: str, use_proxy: bool = False) -> List[Dict]:
        """
        抓取数据

        Args:
            url: 目标URL
            use_proxy: 是否使用代理

        Returns:
            开奖数据列表
        """
        try:
            # 导入反爬虫模块
            from anti_crawler import AdvancedCrawler, CrawlConfig, AntiDetectLevel

            config = CrawlConfig(
                max_retries=3,
                base_delay=2.0,
                anti_detect_level=AntiDetectLevel.ADVANCED
            )
            crawler = AdvancedCrawler(config)

            # 发起请求
            response = crawler.get(url)
            html = response.text

            # 解析数据
            results = self.parser.parse(html)

            logger.info(f"从 {url} 抓取到 {len(results)} 条数据")
            return results

        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return []

    def crawl_all_sources(self) -> Dict[str, List[Dict]]:
        """抓取所有数据源"""
        results = {}

        for source in DATA_SOURCES:
            if not source.enabled:
                continue

            # 根据数据源选择解析器
            if source.code == 'AM':
                self.parser = AMHTMLParser()
            else:
                self.parser = HKHTMLParser()

            data = self.crawl(source.url)
            results[source.code] = data

        return results


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 获取数据源信息
    manager = DataSourceManager()
    info = manager.get_source_info()

    print("=" * 60)
    print("数据源配置")
    print("=" * 60)
    for src in info['all_sources']:
        status = "✓ 启用" if src['enabled'] else "✗ 禁用"
        print(f"{src['name']} ({src['code']}): {src['url']} [{status}]")
    print(f"\n当前活跃: {info['active_source']}")
    print("=" * 60)