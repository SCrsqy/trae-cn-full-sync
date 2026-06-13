"""
Redis缓存与实时更新触发器模块
实现任务锁、缓存管理和实时更新功能
"""
import json
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import redis
except ImportError:
    redis = None


class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db
        self.client = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        if redis is None:
            self.client = MockRedis()
        else:
            try:
                self.client = redis.Redis(host=self.host, port=self.port, db=self.db)
                self.client.ping()
            except:
                # 如果Redis不可用，使用Mock
                self.client = MockRedis()
    
    def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        try:
            result = self.client.get(key)
            return result.decode('utf-8') if result else None
        except:
            return None
    
    def set(self, key: str, value: str, expire: int = 3600):
        """设置缓存"""
        try:
            self.client.set(key, value, ex=expire)
        except:
            pass
    
    def get_json(self, key: str) -> Optional[Dict]:
        """获取JSON格式缓存"""
        data = self.get(key)
        if data:
            try:
                return json.loads(data)
            except:
                return None
        return None
    
    def set_json(self, key: str, value: Dict, expire: int = 3600):
        """设置JSON格式缓存"""
        self.set(key, json.dumps(value), expire)
    
    def acquire_lock(self, lock_name: str, timeout: int = 60) -> bool:
        """获取分布式锁"""
        lock_key = f"lock:{lock_name}"
        # 使用SET NX获取锁
        try:
            result = self.client.set(lock_key, '1', ex=timeout, nx=True)
            return result is not None
        except:
            # Mock模式下使用简单的文件锁
            return True
    
    def release_lock(self, lock_name: str):
        """释放分布式锁"""
        lock_key = f"lock:{lock_name}"
        try:
            self.client.delete(lock_key)
        except:
            pass
    
    def publish(self, channel: str, message: str):
        """发布消息到频道"""
        try:
            self.client.publish(channel, message)
        except:
            pass


class MockRedis:
    """Mock Redis实现（当Redis不可用时使用）"""
    
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key, None)
    
    def set(self, key, value, ex=None):
        self.data[key] = value
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
    
    def publish(self, channel, message):
        pass


class RealTimeUpdater:
    """实时更新触发器"""
    
    def __init__(self, db_path: str, cache: RedisCache):
        self.db_path = db_path
        self.cache = cache
        self.running = False
        self.thread = None
    
    def start(self):
        """启动实时更新服务"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("实时更新触发器已启动")
    
    def stop(self):
        """停止实时更新服务"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("实时更新触发器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._check_new_data()
                self._update_predictions()
                self._update_accuracy()
            except Exception as e:
                print(f"监控循环错误: {e}")
            
            # 每30秒检查一次
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_new_data(self):
        """检查是否有新数据"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取最后更新时间
            last_check = self.cache.get('last_data_check')
            last_check = datetime.fromisoformat(last_check) if last_check else datetime(2000, 1, 1)
            
            # 检查AM数据源
            cursor.execute("SELECT MAX(updated_at) FROM lottery_data_am")
            result = cursor.fetchone()
            if result and result[0]:
                last_update = datetime.fromisoformat(result[0])
                if last_update > last_check:
                    self.cache.set('last_data_check', datetime.now().isoformat())
                    self._notify_update('new_data', {'source': 'AM'})
            
            # 检查HK数据源
            cursor.execute("SELECT MAX(updated_at) FROM lottery_data_hk")
            result = cursor.fetchone()
            if result and result[0]:
                last_update = datetime.fromisoformat(result[0])
                if last_update > last_check:
                    self.cache.set('last_data_check', datetime.now().isoformat())
                    self._notify_update('new_data', {'source': 'HK'})
        
        finally:
            conn.close()
    
    def _update_predictions(self):
        """更新预测"""
        from business_rules import PredictionGenerator
        
        generator = PredictionGenerator(self.db_path)
        
        # 为AM数据源生成预测
        generator.generate_prediction('AM')
        
        # 为HK数据源生成预测
        generator.generate_prediction('HK')
        
        self._notify_update('predictions_updated', {})
    
    def _update_accuracy(self):
        """更新准确率"""
        from business_rules import AccuracyCalculator
        
        calculator = AccuracyCalculator(self.db_path)
        
        # 更新AM数据源准确率
        updated_am = calculator.batch_update_accuracy('AM')
        
        # 更新HK数据源准确率
        updated_hk = calculator.batch_update_accuracy('HK')
        
        if updated_am > 0 or updated_hk > 0:
            self._notify_update('accuracy_updated', {
                'am_updated': updated_am,
                'hk_updated': updated_hk
            })
    
    def _notify_update(self, event_type: str, data: Dict):
        """发送更新通知"""
        message = json.dumps({
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        # 发布到Redis频道
        self.cache.publish('lottery_updates', message)
        
        # 更新缓存
        self.cache.set(f'last_{event_type}', message, expire=300)
        
        print(f"发送更新通知: {event_type}")


class TaskLock:
    """任务锁管理器"""
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
    
    def run_with_lock(self, task_name: str, func, *args, **kwargs):
        """带锁执行任务"""
        if self.cache.acquire_lock(task_name):
            try:
                return func(*args, **kwargs)
            finally:
                self.cache.release_lock(task_name)
        else:
            print(f"任务 {task_name} 正在执行中，跳过")
            return None


# 使用示例
if __name__ == "__main__":
    # 创建缓存实例
    cache = RedisCache()
    
    # 创建实时更新器
    updater = RealTimeUpdater('/Users/rs/AI/分析预测推荐/lottery.db', cache)
    
    # 启动实时更新
    updater.start()
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        updater.stop()