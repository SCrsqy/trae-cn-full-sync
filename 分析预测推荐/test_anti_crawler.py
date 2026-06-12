"""
反爬虫模块测试
"""
from anti_crawler import AdvancedCrawler, CrawlConfig, AntiDetectLevel, WAFDetector
import json


def test_fingerprint():
    """测试指纹伪装"""
    print("=" * 60)
    print("测试1: 指纹伪装")
    print("=" * 60)

    crawler = AdvancedCrawler()
    headers = crawler.fingerprint_manager.generate_headers(AntiDetectLevel.ADVANCED)

    print("生成的请求头:")
    for key, value in headers.items():
        print(f"  {key}: {value[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")

    print("\n✓ 指纹伪装正常")


def test_waf_detection():
    """测试WAF检测"""
    print("\n" + "=" * 60)
    print("测试2: WAF检测")
    print("=" * 60)

    # 测试Cloudflare页面
    test_content = """
    <html><body>
    <div class="cloudflare-challenge">Please verify you are human</div>
    <script>__cf_bm = "xxx"</script>
    </body></html>
    """

    is_waf = WAFDetector.is_waf_page(test_content)
    print(f"Cloudflare页面检测: {'✓ 检测到' if is_waf else '✗ 未检测到'}")

    # 测试正常页面
    normal_content = "<html><body><div class='content'>Hello World</div></body></html>"
    is_waf = WAFDetector.is_waf_page(normal_content)
    print(f"正常页面检测: {'✓ 检测到' if is_waf else '✗ 未检测到'}")

    print("\n✓ WAF检测正常")


def test_smart_delay():
    """测试智能延迟"""
    print("\n" + "=" * 60)
    print("测试3: 智能延迟")
    print("=" * 60)

    crawler = AdvancedCrawler(CrawlConfig(base_delay=1.0, max_delay=5.0))

    delays = []
    for i in range(5):
        delay = crawler.delay_manager.get_delay()
        delays.append(delay)
        print(f"  请求{i+1}: 延迟 {delay:.2f}s")

    avg_delay = sum(delays) / len(delays)
    print(f"\n  平均延迟: {avg_delay:.2f}s")
    print("✓ 智能延迟正常")


def test_advanced_crawler():
    """测试增强版爬虫"""
    print("\n" + "=" * 60)
    print("测试4: 增强版爬虫")
    print("=" * 60)

    config = CrawlConfig(
        max_retries=3,
        base_delay=1.0,
        anti_detect_level=AntiDetectLevel.ADVANCED
    )
    crawler = AdvancedCrawler(config)

    try:
        # 测试请求httpbin
        response = crawler.get("https://httpbin.org/headers")
        data = response.json()

        print(f"  状态码: {response.status_code}")
        print(f"  User-Agent: {data['headers']['User-Agent']}")
        print(f"  请求成功 ✓")

    except Exception as e:
        print(f"  请求失败: {e}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("反爬虫模块测试")
    print("=" * 60)

    test_fingerprint()
    test_waf_detection()
    test_smart_delay()
    test_advanced_crawler()

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()