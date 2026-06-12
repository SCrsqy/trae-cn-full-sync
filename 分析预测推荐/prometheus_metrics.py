"""
Prometheus监控指标模块
暴露metrics端点供Prometheus抓取
集成到Flask/FastAPI应用
"""
from flask import Flask, Response, jsonify
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)
from functools import wraps
import time
from typing import Callable


# =====================================================
# 定义监控指标
# =====================================================

# 1. 爬虫相关指标
CRAWL_REQUESTS_TOTAL = Counter(
    'crawl_requests_total',
    'Total crawl requests',
    ['source', 'status']  # source: AM/HK, status: success/failed/timeout
)

CRAWL_LATENCY_SECONDS = Histogram(
    'crawl_latency_seconds',
    'Crawl request latency',
    ['source'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

CRAWL_DATA_FRESHNESS = Gauge(
    'crawl_data_freshness_hours',
    'Hours since last successful crawl',
    ['source']
)

# 2. 数据处理相关指标
DATA_PROCESSING_TOTAL = Counter(
    'data_processing_total',
    'Total data processing operations',
    ['operation', 'status']  # operation: parse/validate/insert, status: success/failed
)

DATA_VALIDATION_ERRORS = Counter(
    'data_validation_errors_total',
    'Total data validation errors',
    ['error_type']  # error_type: missing_field/invalid_format/inconsistency
)

# 3. 预测相关指标
PREDICTION_GENERATED_TOTAL = Counter(
    'prediction_generated_total',
    'Total predictions generated',
    ['source', 'status']
)

PREDICTION_ACCURACY = Histogram(
    'prediction_accuracy_percent',
    'Prediction accuracy percentage',
    ['source', 'prediction_type'],  # prediction_type: top6/triple4/top12/combined
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
)

# 4. 数据库相关指标
DB_CONNECTIONS_ACTIVE = Gauge(
    'db_connections_active',
    'Number of active database connections',
    ['db_name']  # db_name: primary/replica
)

DB_QUERY_LATENCY_SECONDS = Histogram(
    'db_query_latency_seconds',
    'Database query latency',
    ['query_type'],  # query_type: select/insert/update
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

DB_OPERATIONS_TOTAL = Counter(
    'db_operations_total',
    'Total database operations',
    ['operation', 'status']
)

# 5. 系统相关指标
SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)

# 6. 业务告警指标
BUSINESS_ALERTS = Counter(
    'business_alerts_total',
    'Total business alerts triggered',
    ['alert_type', 'severity']  # alert_type: data_missing/accuracy_low/consistent_error, severity: warning/critical
)

# =====================================================
# 辅助函数
# =====================================================

def track_request_duration(metric: Histogram, labels: dict = None):
    """装饰器: 跟踪函数执行时间"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator


def increment_counter(metric: Counter, labels: dict = None):
    """辅助函数: 增加计数器"""
    if labels:
        metric.labels(**labels).inc()
    else:
        metric.inc()


# =====================================================
# Flask集成
# =====================================================

def create_metrics_app() -> Flask:
    """创建metrics Flask应用"""
    app = Flask(__name__)

    @app.route('/metrics')
    def metrics():
        """Prometheus抓取端点"""
        return Response(
            generate_latest(REGISTRY),
            mimetype=CONTENT_TYPE_LATEST
        )

    @app.route('/health')
    def health():
        """健康检查端点"""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time()
        })

    @app.route('/health/ready')
    def ready():
        """就绪检查端点"""
        # TODO: 检查数据库、Redis等依赖
        return jsonify({
            'status': 'ready',
            'checks': {
                'database': 'ok',
                'redis': 'ok',
                'crawler': 'ok'
            }
        })

    return app


# =====================================================
# 中间件示例
# =====================================================

def setup_request_metrics(app: Flask):
    """为Flask应用添加请求指标中间件"""

    @app.before_request
    def before_request():
        from flask import g
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        from flask import g, request
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            CRAWL_LATENCY_SECONDS.labels(
                source=request.endpoint or 'unknown'
            ).observe(duration)
        return response


# =====================================================
# 业务指标记录函数
# =====================================================

def record_crawl_success(source: str, latency: float):
    """记录爬虫成功"""
    CRAWL_REQUESTS_TOTAL.labels(source=source, status='success').inc()
    CRAWL_LATENCY_SECONDS.labels(source=source).observe(latency)
    CRAWL_DATA_FRESHNESS.labels(source=source).set(0)


def record_crawl_failure(source: str, error_type: str):
    """记录爬虫失败"""
    CRAWL_REQUESTS_TOTAL.labels(source=source, status='failed').inc()
    BUSINESS_ALERTS.labels(
        alert_type='crawl_failure',
        severity='warning' if error_type == 'timeout' else 'critical'
    ).inc()


def record_data_validation_error(error_type: str):
    """记录数据校验错误"""
    DATA_VALIDATION_ERRORS.labels(error_type=error_type).inc()
    BUSINESS_ALERTS.labels(
        alert_type='data_validation',
        severity='warning'
    ).inc()


def record_prediction_accuracy(source: str, prediction_type: str, accuracy: float):
    """记录预测准确率"""
    PREDICTION_ACCURACY.labels(
        source=source,
        prediction_type=prediction_type
    ).observe(accuracy)


def record_business_alert(alert_type: str, severity: str):
    """记录业务告警"""
    BUSINESS_ALERTS.labels(alert_type=alert_type, severity=severity).inc()


# =====================================================
# 独立运行
# =====================================================

if __name__ == '__main__':
    # 模拟一些指标
    record_crawl_success('AM', 1.5)
    record_crawl_success('HK', 2.3)
    record_prediction_accuracy('AM', 'top6', 50.0)
    record_prediction_accuracy('AM', 'combined', 44.3)
    record_business_alert('accuracy_low', 'warning')

    # 创建并启动app
    app = create_metrics_app()
    app.run(host='0.0.0.0', port=9090)