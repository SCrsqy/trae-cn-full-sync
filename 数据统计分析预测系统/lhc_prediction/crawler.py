import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import time
import random
from datetime import datetime, timedelta
from config import AM_URL, HK_URL, USER_AGENT, DATABASE_PATH, ZODIAC_MAP
from lunar_utils import get_zodiac_by_date

def get_headers():
    """生成随机请求头，模拟真实浏览器"""
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/605.1.15'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.google.com/'
    }
    return headers

def fetch_page(url, max_retries=3):
    """获取网页内容，支持重试机制"""
    session = requests.Session()
    
    for attempt in range(max_retries):
        try:
            headers = get_headers()
            print(f'正在尝试获取数据 (第{attempt+1}次): {url}')
            
            # 添加随机延迟，模拟人类行为
            if attempt > 0:
                delay = random.uniform(2, 5)
                time.sleep(delay)
            
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # 检查是否被重定向到其他页面
            if response.url != url:
                print(f'被重定向到: {response.url}')
            
            print(f'成功获取数据，内容长度: {len(response.text)}')
            return response.text
            
        except requests.exceptions.HTTPError as e:
            print(f'HTTP错误: {e}')
            if attempt < max_retries - 1:
                print(f'等待后重试...')
                time.sleep(random.uniform(3, 6))
            else:
                print(f'达到最大重试次数，获取失败')
                return None
                
        except requests.exceptions.RequestException as e:
            print(f'网络请求失败: {e}')
            if attempt < max_retries - 1:
                print(f'等待后重试...')
                time.sleep(random.uniform(3, 6))
            else:
                return None
    
    return None

def parse_am_data(html):
    """解析澳门六合彩数据"""
    results = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试多种表格定位方式
        tables = soup.find_all('table')
        if not tables:
            # 尝试查找div中的数据
            divs = soup.find_all('div', class_=re.compile(r'(result|data|lottery|kj)', re.I))
            for div in divs:
                text = div.get_text()
                if '期' in text or '开奖' in text:
                    # 尝试从文本中提取数据
                    pass
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        # 尝试多种解析方式
                        issue_str = cells[0].get_text(strip=True)
                        date_str = cells[1].get_text(strip=True)
                        numbers_str = cells[2].get_text(strip=True)
                        special_str = cells[3].get_text(strip=True)
                        
                        # 清理数据
                        issue_str = re.sub(r'[^\d]', '', issue_str)
                        date_str = re.sub(r'[^\d\-\/]', '', date_str)
                        
                        if issue_str and date_str:
                            # 解析号码
                            numbers = []
                            for n in re.findall(r'\d{1,2}', numbers_str):
                                num = int(n)
                                if 1 <= num <= 49:
                                    numbers.append(num)
                            
                            special_number = None
                            for n in re.findall(r'\d{1,2}', special_str):
                                num = int(n)
                                if 1 <= num <= 49:
                                    special_number = num
                                    break
                            
                            if len(numbers) >= 6 and special_number:
                                zodiac = get_zodiac_by_date(date_str)
                                results.append({
                                    'issue': issue_str,
                                    'draw_date': date_str,
                                    'numbers': ','.join(map(str, numbers[:6])),
                                    'special_number': special_number,
                                    'zodiac': zodiac
                                })
                    except Exception as e:
                        continue
        
        print(f'解析澳门数据: 找到{len(results)}条记录')
        return results
        
    except Exception as e:
        print(f'解析澳门数据失败: {e}')
        return []

def parse_hk_data(html):
    """解析香港六合彩数据"""
    results = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        issue_str = cells[0].get_text(strip=True)
                        date_str = cells[1].get_text(strip=True)
                        numbers_str = cells[2].get_text(strip=True)
                        special_str = cells[3].get_text(strip=True)
                        
                        issue_str = re.sub(r'[^\d]', '', issue_str)
                        date_str = re.sub(r'[^\d\-\/]', '', date_str)
                        
                        if issue_str and date_str:
                            numbers = []
                            for n in re.findall(r'\d{1,2}', numbers_str):
                                num = int(n)
                                if 1 <= num <= 49:
                                    numbers.append(num)
                            
                            special_number = None
                            for n in re.findall(r'\d{1,2}', special_str):
                                num = int(n)
                                if 1 <= num <= 49:
                                    special_number = num
                                    break
                            
                            if len(numbers) >= 6 and special_number:
                                zodiac = get_zodiac_by_date(date_str)
                                results.append({
                                    'issue': issue_str,
                                    'draw_date': date_str,
                                    'numbers': ','.join(map(str, numbers[:6])),
                                    'special_number': special_number,
                                    'zodiac': zodiac
                                })
                    except Exception as e:
                        continue
        
        print(f'解析香港数据: 找到{len(results)}条记录')
        return results
        
    except Exception as e:
        print(f'解析香港数据失败: {e}')
        return []

def generate_mock_data(region, count=50):
    """生成模拟数据（用于演示和测试）"""
    results = []
    base_date = datetime.now() - timedelta(days=count)
    
    for i in range(count):
        # 生成期号
        issue = f'2026{str(i+100).zfill(3)}'
        
        # 生成开奖日期
        draw_date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        # 随机生成6个平码（1-49，不重复）
        numbers = random.sample(range(1, 50), 6)
        numbers_str = ','.join(map(str, sorted(numbers)))
        
        # 随机生成特码（排除已选的平码）
        remaining = [n for n in range(1, 50) if n not in numbers]
        special_number = random.choice(remaining)
        
        # 获取生肖
        zodiac = get_zodiac_by_date(draw_date)
        
        results.append({
            'issue': issue,
            'draw_date': draw_date,
            'numbers': numbers_str,
            'special_number': special_number,
            'zodiac': zodiac
        })
    
    print(f'生成{region}模拟数据: {count}条')
    return results

def save_to_db(region, data):
    """保存数据到数据库"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    count = 0
    
    for item in data:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO draw_results 
                (region, issue, draw_date, numbers, special_number, zodiac)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (region, item['issue'], item['draw_date'], item['numbers'], 
                  item['special_number'], item['zodiac']))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            print(f'保存数据失败: {e}')
    
    conn.commit()
    conn.close()
    return count

def crawl(region, use_mock=False):
    """爬取数据的主函数"""
    if region == 'am':
        url = AM_URL
        parser = parse_am_data
    elif region == 'hk':
        url = HK_URL
        parser = parse_hk_data
    else:
        print('无效地区')
        return 0
    
    # 首先尝试从真实网站爬取
    html = fetch_page(url)
    
    if html:
        data = parser(html)
        if data:
            return save_to_db(region, data)
    
    # 如果爬取失败，使用模拟数据
    if use_mock or not html:
        print(f'网站爬取失败，使用模拟数据')
        mock_data = generate_mock_data(region, 30)
        return save_to_db(region, mock_data)
    
    return 0

if __name__ == '__main__':
    print('开始爬取数据...')
    
    am_count = crawl('am', use_mock=True)
    print(f'澳门数据更新: {am_count} 条')
    
    hk_count = crawl('hk', use_mock=True)
    print(f'香港数据更新: {hk_count} 条')
    
    print('数据爬取完成')