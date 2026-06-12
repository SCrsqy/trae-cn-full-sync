"""
增强版反爬虫机制
整合WAF处理、指纹伪装、智能翻页、异步控制等策略
"""
import random
import time
import re
import json
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import uuid

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


from enum import Enum, IntEnum

class AntiDetectLevel(IntEnum):
    """反检测级别"""
    BASIC = 1       # 基础伪装
    MEDIUM = 2      # 中等伪装
    ADVANCED = 3    # 高级伪装


@dataclass
class CrawlConfig:
    """爬虫配置"""
    max_retries: int = 3
    base_delay: float = 1.0  # 基础请求间隔
    max_delay: float = 10.0  # 最大请求间隔
    timeout: float = 30.0
    anti_detect_level: AntiDetectLevel = AntiDetectLevel.ADVANCED
    use_proxy: bool = False
    proxy_pool_size: int = 10


class FingerprintManager:
    """指纹管理器：生成和管理浏览器指纹"""

    # 浏览器版本池
    BROWSERS = [
        {
            'name': 'Chrome',
            'version': '120.0.6099.109',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.109 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        },
        {
            'name': 'Chrome macOS',
            'version': '120.0.6099.109',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.109 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        },
        {
            'name': 'Firefox',
            'version': '121.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        },
        {
            'name': 'Safari',
            'version': '17.1',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
    ]

    # 语言和编码
    ACCEPT_LANGUAGES = [
        'zh-CN,zh;q=0.9,en;q=0.8',
        'zh-CN,zh;q=0.9',
        'zh-TW,zh;q=0.9,en;q=0.8',
    ]

    # 屏幕分辨率
    SCREEN_RESOLUTIONS = [
        '1920x1080',
        '1366x768',
        '1536x864',
        '2560x1440',
    ]

    def __init__(self):
        self.current_browser = None
        self.session_id = str(uuid.uuid4())[:8]

    def get_random_browser(self):
        """随机选择浏览器"""
        self.current_browser = random.choice(self.BROWSERS)
        return self.current_browser

    def generate_headers(self, anti_detect_level: AntiDetectLevel = AntiDetectLevel.ADVANCED) -> Dict[str, str]:
        """生成伪装请求头"""
        browser = self.get_random_browser()

        headers = {
            'User-Agent': browser['user_agent'],
            'Accept': browser['accept'],
            'Accept-Language': random.choice(self.ACCEPT_LANGUAGES),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }

        if anti_detect_level >= AntiDetectLevel.MEDIUM:
            headers.update({
                'Sec-Ch-Ua': f'"{browser["name"]}";v="{browser["version"].split(".")[0]}", "Not:A-Brand";v="8", "Chromium";v="{browser["version"].split(".")[0]}"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            })

        if anti_detect_level == AntiDetectLevel.ADVANCED:
            headers.update({
                'Dnt': '1',
                'Sec-Gpc': '1',
                'Referer': self._generate_random_referer(),
                'Origin': self._generate_random_origin(),
            })

        return headers

    def _generate_random_referer(self) -> str:
        """生成随机referer"""
        referers = [
            'https://www.google.com/',
            'https://www.baidu.com/',
            'https://www.bing.com/',
            'https://www.google.com/search?q=lottery',
            'https://www.baidu.com/s?wd=lottery',
        ]
        return random.choice(referers)

    def _generate_random_origin(self) -> str:
        """生成随机origin"""
        origins = [
            'https://example.com',
            'https://www.example.com',
        ]
        return random.choice(origins)


class WAFDetector:
    """WAF检测器"""

    WAF_SIGNATURES = [
        # Cloudflare
        ('cf-ray', 'Cloudflare'),
        ('__cf_bm', 'Cloudflare'),
        ('cloudflare', 'Cloudflare'),
        # Akamai
        ('akamai', 'Akamai'),
        # 验证码相关
        ('captcha', 'Captcha'),
        ('verify', 'Verification'),
        ('challenge', 'Challenge'),
        # 常见WAF页面特征
        ('403 Forbidden', 'WAF'),
        ('Access Denied', 'WAF'),
        ('Too Many Requests', 'Rate Limit'),
        ('Security Check', 'Security Check'),
        ('DDOS Protection', 'DDOS Protection'),
    ]

    @classmethod
    def detect_waf(cls, response) -> Optional[str]:
        """检测响应是否被WAF拦截"""
        # 检查状态码
        if response.status_code in [403, 429, 503]:
            return 'WAF Block'

        # 检查headers
        for header, waf_type in cls.WAF_SIGNATURES:
            if header.lower() in [h.lower() for h in response.headers]:
                return waf_type

        # 检查响应内容
        content = response.text.lower()
        for signature, waf_type in cls.WAF_SIGNATURES:
            if signature.lower() in content:
                return waf_type

        return None

    @classmethod
    def is_waf_page(cls, content: str) -> bool:
        """判断是否是WAF页面"""
        waf_patterns = [
            r'<form.*captcha',
            r'cloudflare.*challenge',
            r'access.*denied',
            r'security.*check',
            r'recaptcha',
        ]
        content_lower = content.lower()
        return any(re.search(pattern, content_lower) for pattern in waf_patterns)

    @classmethod
    def extract_render_data(cls, content: str) -> Optional[str]:
        """从WAF页面提取renderData"""
        match = re.search(r'renderData\s*=\s*["\'](.*?)["\']', content)
        if match:
            return match.group(1)
        # 尝试JSON格式
        match = re.search(r'<textarea[^>]*>(.*?)</textarea>', content)
        if match:
            return match.group(1)
        return None


class SmartDelayManager:
    """智能延迟管理器"""

    def __init__(self, base_delay: float = 1.0, max_delay: float = 10.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.request_count = 0
        self.last_request_time = 0
        self.delay_factor = 1.0

    def get_delay(self) -> float:
        """计算请求间隔"""
        # 基础随机延迟
        delay = random.uniform(self.base_delay, self.base_delay * 2)

        # 请求频率控制
        now = time.time()
        if now - self.last_request_time < self.base_delay * 0.5:
            self.delay_factor = min(self.delay_factor * 1.5, 5.0)
        else:
            self.delay_factor = max(self.delay_factor * 0.8, 1.0)

        delay *= self.delay_factor

        # 每100次请求增加额外延迟
        self.request_count += 1
        if self.request_count % 100 == 0:
            delay += random.uniform(5, 15)

        # 限制最大延迟
        return min(delay, self.max_delay)

    def reset(self):
        """重置状态"""
        self.request_count = 0
        self.delay_factor = 1.0

    def wait(self):
        """执行等待"""
        delay = self.get_delay()
        time.sleep(delay)


class AdvancedCrawler:
    """
    增强版爬虫
    包含完整的反爬虫策略
    """

    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()
        self.fingerprint_manager = FingerprintManager()
        self.delay_manager = SmartDelayManager(
            base_delay=self.config.base_delay,
            max_delay=self.config.max_delay
        )
        self.session = None
        self.cookies = {}

    def _init_session(self):
        """初始化请求会话"""
        if requests is None:
            raise ImportError("requests library is required")

        session = requests.Session()

        # 配置连接池和重试
        retry_strategy = Retry(
            total=0,  # 我们自己控制重试
            backoff_factor=0,
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 设置默认超时
        session.timeout = self.config.timeout

        self.session = session

    def _handle_waf(self, response) -> bool:
        """处理WAF拦截"""
        waf_type = WAFDetector.detect_waf(response)
        if not waf_type:
            return False

        logger.warning(f"WAF detected: {waf_type}")

        # 尝试从页面提取数据
        render_data = WAFDetector.extract_render_data(response.text)
        if render_data:
            logger.info("Extracted renderData from WAF page")
            return True

        # 尝试重新获取cookie
        self._refresh_cookies(response.url)
        return False

    def _refresh_cookies(self, url: str):
        """刷新cookie"""
        try:
            # 访问首页获取新cookie
            headers = self.fingerprint_manager.generate_headers(
                anti_detect_level=self.config.anti_detect_level
            )
            response = self.session.get(url, headers=headers)
            self.cookies.update(response.cookies.get_dict())
            logger.info("Cookies refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh cookies: {e}")

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Any:
        """带重试的请求"""
        if self.session is None:
            self._init_session()

        for attempt in range(self.config.max_retries):
            try:
                # 智能延迟
                if attempt > 0:
                    self.delay_manager.wait()

                # 生成伪装headers
                headers = self.fingerprint_manager.generate_headers(
                    anti_detect_level=self.config.anti_detect_level
                )

                # 合并headers
                if 'headers' in kwargs:
                    headers.update(kwargs['headers'])
                kwargs['headers'] = headers

                # 添加cookie
                if self.cookies:
                    self.session.cookies.update(self.cookies)

                # 执行请求
                response = self.session.request(method, url, **kwargs)

                # 检查WAF
                if self._handle_waf(response):
                    continue

                response.raise_for_status()

                # 更新cookie
                self.cookies.update(response.cookies.get_dict())

                return response

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}): {e}")

                # 增加延迟因子
                self.delay_manager.delay_factor = min(
                    self.delay_manager.delay_factor * 2, 10.0
                )

                if attempt == self.config.max_retries - 1:
                    raise

        raise Exception("Max retries exceeded")

    def get(self, url: str, **kwargs) -> Any:
        """GET请求"""
        return self._request_with_retry('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> Any:
        """POST请求"""
        return self._request_with_retry('POST', url, **kwargs)

    def crawl_with_pagination(self, url: str, parser: Callable, max_pages: int = 10) -> List:
        """带分页的爬取"""
        results = []
        current_page = 1
        has_next = True

        while has_next and current_page <= max_pages:
            try:
                page_url = self._build_page_url(url, current_page)
                response = self.get(page_url)

                # 解析当前页数据
                page_data = parser(response.text)
                results.extend(page_data)

                # 检查是否有下一页
                has_next = self._has_next_page(response.text, current_page)
                current_page += 1

                # 请求间隔
                self.delay_manager.wait()

            except Exception as e:
                logger.error(f"Error crawling page {current_page}: {e}")
                break

        return results

    def _build_page_url(self, base_url: str, page: int) -> str:
        """构建分页URL"""
        if 'page=' in base_url:
            return re.sub(r'page=\d+', f'page={page}', base_url)
        elif '?' in base_url:
            return f"{base_url}&page={page}"
        else:
            return f"{base_url}?page={page}"

    def _has_next_page(self, content: str, current_page: int) -> bool:
        """检查是否有下一页"""
        # 检查常见的下一页标识
        patterns = [
            f'下一页',
            f'next.*page',
            f'page.*{current_page + 1}',
            f'>{current_page}<',
        ]
        content_lower = content.lower()
        return any(re.search(pattern.lower(), content_lower) for pattern in patterns)


class AsyncCrawlManager:
    """异步爬取管理器"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.active_tasks = 0
        self.task_queue = []

    def add_task(self, url: str, callback: Callable):
        """添加爬取任务"""
        self.task_queue.append((url, callback))

    async def run(self, crawler: AdvancedCrawler):
        """执行所有任务"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        async def crawl_task(url, callback):
            nonlocal self
            self.active_tasks += 1
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: crawler.get(url)
                )
                callback(response)
            finally:
                self.active_tasks -= 1

        # 分批执行，控制并发
        while self.task_queue:
            batch = self.task_queue[:self.max_concurrent]
            self.task_queue = self.task_queue[self.max_concurrent:]

            tasks = [crawl_task(url, callback) for url, callback in batch]
            await asyncio.gather(*tasks)

            # 批次间隔
            await asyncio.sleep(random.uniform(2, 5))


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 创建增强版爬虫
    config = CrawlConfig(
        max_retries=5,
        base_delay=2.0,
        anti_detect_level=AntiDetectLevel.ADVANCED
    )
    crawler = AdvancedCrawler(config)

    # 测试请求
    try:
        response = crawler.get("https://httpbin.org/headers")
        data = response.json()
        print("请求成功！")
        print(f"User-Agent: {data['headers']['User-Agent']}")
    except Exception as e:
        print(f"请求失败: {e}")

    # 测试WAF检测
    test_content = """
    <html><body>
    <div class="cloudflare-challenge">Please verify you are human</div>
    </body></html>
    """
    waf_type = WAFDetector.detect_waf(None)  # 需要完整响应对象
    print(f"WAF检测测试完成")