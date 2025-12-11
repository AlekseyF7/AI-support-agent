"""
Тесты для утилит
"""
import pytest
import time
from bot.utils.retry import retry_with_backoff, RetryableAPI
from bot.utils.cache import CacheManager
from bot.utils.rate_limiter import RateLimiter
from bot.utils.metrics import MetricsCollector


class TestRetry:
    """Тесты для retry-логики"""
    
    def test_retry_success(self):
        """Тест успешного выполнения без retry"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3)
        def successful_function():
            call_count[0] += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retry_with_failures(self):
        """Тест retry при ошибках"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Test error")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count[0] == 3
    
    def test_retry_exhausted(self):
        """Тест исчерпания попыток"""
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def always_failing():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_failing()
    
    def test_retryable_api(self):
        """Тест класса RetryableAPI"""
        api = RetryableAPI(max_retries=2, initial_delay=0.1)
        call_count = [0]
        
        def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Fail")
            return "success"
        
        result = api.call_with_retry(test_func)
        assert result == "success"
        assert call_count[0] == 2


class TestCache:
    """Тесты для кэширования"""
    
    def test_cache_set_get(self):
        """Тест установки и получения из кэша"""
        cache = CacheManager(use_redis=False)
        
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")
        
        assert value == "test_value"
    
    def test_cache_expiration(self):
        """Тест истечения срока кэша"""
        cache = CacheManager(use_redis=False)
        
        cache.set("test_key", "test_value", ttl=0.1)
        time.sleep(0.2)
        value = cache.get("test_key")
        
        assert value is None
    
    def test_cache_delete(self):
        """Тест удаления из кэша"""
        cache = CacheManager(use_redis=False)
        
        cache.set("test_key", "test_value")
        cache.delete("test_key")
        value = cache.get("test_key")
        
        assert value is None
    
    def test_cache_decorator(self):
        """Тест декоратора кэширования"""
        cache = CacheManager(use_redis=False)
        call_count = [0]
        
        @cache.cache_result(prefix="test", ttl=60)
        def cached_function(x):
            call_count[0] += 1
            return x * 2
        
        result1 = cached_function(5)
        result2 = cached_function(5)
        
        assert result1 == 10
        assert result2 == 10
        assert call_count[0] == 1  # Функция должна быть вызвана только один раз


class TestRateLimiter:
    """Тесты для rate limiter"""
    
    def test_rate_limit_allowed(self):
        """Тест разрешенного запроса"""
        limiter = RateLimiter()
        limiter.set_limit("test_action", max_requests=5, window_seconds=60)
        
        assert limiter.is_allowed(12345, "test_action") is True
    
    def test_rate_limit_exceeded(self):
        """Тест превышения лимита"""
        limiter = RateLimiter()
        limiter.set_limit("test_action", max_requests=2, window_seconds=60)
        
        assert limiter.is_allowed(12345, "test_action") is True
        assert limiter.is_allowed(12345, "test_action") is True
        assert limiter.is_allowed(12345, "test_action") is False
    
    def test_rate_limit_remaining(self):
        """Тест получения оставшихся запросов"""
        limiter = RateLimiter()
        limiter.set_limit("test_action", max_requests=5, window_seconds=60)
        
        limiter.is_allowed(12345, "test_action")
        remaining = limiter.get_remaining(12345, "test_action")
        
        assert remaining == 4
    
    def test_rate_limit_reset(self):
        """Тест сброса лимита"""
        limiter = RateLimiter()
        limiter.set_limit("test_action", max_requests=2, window_seconds=60)
        
        limiter.is_allowed(12345, "test_action")
        limiter.is_allowed(12345, "test_action")
        limiter.reset(12345, "test_action")
        
        assert limiter.is_allowed(12345, "test_action") is True


class TestMetrics:
    """Тесты для метрик"""
    
    def test_metrics_increment(self):
        """Тест увеличения счетчика"""
        metrics = MetricsCollector()
        
        metrics.increment("test_counter")
        metrics.increment("test_counter", value=5)
        
        assert metrics.get_counter("test_counter") == 6
    
    def test_metrics_timing(self):
        """Тест записи времени выполнения"""
        metrics = MetricsCollector()
        
        metrics.record_timing("test_timing", 1.5)
        metrics.record_timing("test_timing", 2.5)
        
        avg = metrics.get_average_timing("test_timing")
        assert avg == 2.0
    
    def test_metrics_percentile(self):
        """Тест расчета перцентиля"""
        metrics = MetricsCollector()
        
        for i in range(100):
            metrics.record_timing("test_timing", float(i))
        
        p95 = metrics.get_percentile_timing("test_timing", 95.0)
        assert p95 is not None
        assert p95 >= 94
    
    def test_metrics_user_action(self):
        """Тест записи действия пользователя"""
        metrics = MetricsCollector()
        
        metrics.record_user_action(12345, "message_sent", 1)
        metrics.record_user_action(12345, "message_sent", 2)
        
        user_stats = metrics.get_user_stats(12345)
        assert user_stats["message_sent"] == 3
    
    def test_metrics_stats(self):
        """Тест получения статистики"""
        metrics = MetricsCollector()
        
        metrics.increment("test_counter")
        metrics.record_timing("test_timing", 1.0)
        
        stats = metrics.get_stats()
        assert "counters" in stats
        assert "averages" in stats
        assert stats["counters"]["test_counter"] == 1
