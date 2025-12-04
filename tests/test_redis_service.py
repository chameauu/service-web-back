"""
Test suite for Redis Cache Service
Following TDD approach - tests written first
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from src.services.redis_cache import RedisCacheService


@pytest.fixture
def redis_service():
    """Fixture to create Redis service instance"""
    service = RedisCacheService()
    yield service
    # Cleanup after tests
    if service.is_available():
        service.flush_test_data()


class TestRedisConnection:
    """Test Redis connection and availability"""
    
    def test_redis_is_available(self, redis_service):
        """Test that Redis service is available"""
        assert redis_service.is_available() is True
    
    def test_redis_client_exists(self, redis_service):
        """Test that Redis client is created"""
        assert redis_service.client is not None
    
    def test_ping_redis(self, redis_service):
        """Test Redis ping command"""
        result = redis_service.ping()
        assert result is True


class TestDeviceCache:
    """Test device caching operations"""
    
    def test_cache_device_info(self, redis_service):
        """Test caching device information"""
        device_id = 1
        device_data = {
            'id': device_id,
            'name': 'Test Device',
            'status': 'active',
            'user_id': 100
        }
        
        result = redis_service.cache_device(device_id, device_data, ttl=3600)
        assert result is True
    
    def test_get_cached_device(self, redis_service):
        """Test retrieving cached device"""
        device_id = 1
        device_data = {'id': device_id, 'name': 'Test Device'}
        
        redis_service.cache_device(device_id, device_data)
        result = redis_service.get_device(device_id)
        
        assert result is not None
        assert result['id'] == device_id
        assert result['name'] == 'Test Device'
    
    def test_cache_device_with_ttl(self, redis_service):
        """Test device cache with TTL expiration"""
        device_id = 1
        device_data = {'id': device_id}
        
        redis_service.cache_device(device_id, device_data, ttl=1)
        time.sleep(2)
        
        result = redis_service.get_device(device_id)
        assert result is None
    
    def test_delete_device_cache(self, redis_service):
        """Test deleting device from cache"""
        device_id = 1
        device_data = {'id': device_id}
        
        redis_service.cache_device(device_id, device_data)
        redis_service.delete_device(device_id)
        
        result = redis_service.get_device(device_id)
        assert result is None


class TestAPIKeyCache:
    """Test API key caching"""
    
    def test_cache_api_key(self, redis_service):
        """Test caching API key to device mapping"""
        api_key = 'test_api_key_123'
        device_data = {
            'device_id': 1,
            'user_id': 100,
            'status': 'active'
        }
        
        result = redis_service.cache_api_key(api_key, device_data, ttl=3600)
        assert result is True
    
    def test_get_device_by_api_key(self, redis_service):
        """Test retrieving device by API key"""
        api_key = 'test_api_key_123'
        device_data = {'device_id': 1, 'status': 'active'}
        
        redis_service.cache_api_key(api_key, device_data)
        result = redis_service.get_device_by_api_key(api_key)
        
        assert result is not None
        assert result['device_id'] == 1
    
    def test_invalidate_api_key(self, redis_service):
        """Test invalidating API key cache"""
        api_key = 'test_api_key_123'
        device_data = {'device_id': 1}
        
        redis_service.cache_api_key(api_key, device_data)
        redis_service.invalidate_api_key(api_key)
        
        result = redis_service.get_device_by_api_key(api_key)
        assert result is None


class TestDeviceStatus:
    """Test device status caching"""
    
    def test_set_device_online(self, redis_service):
        """Test marking device as online"""
        device_id = 1
        
        result = redis_service.set_device_online(device_id)
        assert result is True
    
    def test_set_device_offline(self, redis_service):
        """Test marking device as offline"""
        device_id = 1
        
        result = redis_service.set_device_offline(device_id)
        assert result is True
    
    def test_is_device_online(self, redis_service):
        """Test checking if device is online"""
        device_id = 1
        
        redis_service.set_device_online(device_id)
        result = redis_service.is_device_online(device_id)
        
        assert result is True
    
    def test_get_online_devices(self, redis_service):
        """Test getting list of online devices"""
        redis_service.set_device_online(1)
        redis_service.set_device_online(2)
        redis_service.set_device_offline(3)
        
        result = redis_service.get_online_devices()
        
        assert isinstance(result, list)
        assert 1 in result
        assert 2 in result
        assert 3 not in result
    
    def test_update_device_last_seen(self, redis_service):
        """Test updating device last seen timestamp"""
        device_id = 1
        
        result = redis_service.update_last_seen(device_id)
        assert result is True
        
        last_seen = redis_service.get_last_seen(device_id)
        assert last_seen is not None


class TestLatestTelemetry:
    """Test latest telemetry caching"""
    
    def test_cache_latest_telemetry(self, redis_service):
        """Test caching latest telemetry values"""
        device_id = 1
        telemetry = {
            'temperature': 23.5,
            'humidity': 65.2,
            'pressure': 1013.25
        }
        
        result = redis_service.cache_latest_telemetry(device_id, telemetry, ttl=600)
        assert result is True
    
    def test_get_latest_telemetry(self, redis_service):
        """Test retrieving latest telemetry"""
        device_id = 1
        telemetry = {'temperature': 23.5, 'humidity': 65.2}
        
        redis_service.cache_latest_telemetry(device_id, telemetry)
        result = redis_service.get_latest_telemetry(device_id)
        
        assert result is not None
        assert result['temperature'] == 23.5
        assert result['humidity'] == 65.2
    
    def test_update_single_measurement(self, redis_service):
        """Test updating a single measurement in latest telemetry"""
        device_id = 1
        
        redis_service.cache_latest_telemetry(device_id, {'temperature': 23.5})
        redis_service.update_measurement(device_id, 'humidity', 65.2)
        
        result = redis_service.get_latest_telemetry(device_id)
        assert result['temperature'] == 23.5
        assert result['humidity'] == 65.2
    
    def test_get_specific_measurement(self, redis_service):
        """Test getting a specific measurement value"""
        device_id = 1
        telemetry = {'temperature': 23.5, 'humidity': 65.2}
        
        redis_service.cache_latest_telemetry(device_id, telemetry)
        result = redis_service.get_measurement(device_id, 'temperature')
        
        assert result == 23.5


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_check_rate_limit(self, redis_service):
        """Test rate limit checking"""
        key = 'device:1'
        max_requests = 10
        window = 60
        
        # Should allow first request
        result = redis_service.check_rate_limit(key, max_requests, window)
        assert result is True
    
    def test_rate_limit_exceeded(self, redis_service):
        """Test rate limit exceeded"""
        key = 'device:1'
        max_requests = 5
        window = 60
        
        # Make requests up to limit
        for i in range(max_requests):
            redis_service.check_rate_limit(key, max_requests, window)
        
        # Next request should be denied
        result = redis_service.check_rate_limit(key, max_requests, window)
        assert result is False
    
    def test_rate_limit_reset(self, redis_service):
        """Test rate limit resets after window"""
        key = 'device:1'
        max_requests = 5
        window = 1  # 1 second window
        
        # Exhaust limit
        for i in range(max_requests):
            redis_service.check_rate_limit(key, max_requests, window)
        
        # Wait for window to expire
        time.sleep(2)
        
        # Should allow again
        result = redis_service.check_rate_limit(key, max_requests, window)
        assert result is True
    
    def test_get_rate_limit_remaining(self, redis_service):
        """Test getting remaining rate limit"""
        key = 'device:1'
        max_requests = 10
        window = 60
        
        redis_service.check_rate_limit(key, max_requests, window)
        redis_service.check_rate_limit(key, max_requests, window)
        
        remaining = redis_service.get_rate_limit_remaining(key, max_requests)
        assert remaining == 8


class TestSessionCache:
    """Test user session caching"""
    
    def test_cache_user_session(self, redis_service):
        """Test caching user session"""
        user_id = 100
        session_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'is_admin': False
        }
        
        result = redis_service.cache_session(user_id, session_data, ttl=1800)
        assert result is True
    
    def test_get_user_session(self, redis_service):
        """Test retrieving user session"""
        user_id = 100
        session_data = {'username': 'testuser'}
        
        redis_service.cache_session(user_id, session_data)
        result = redis_service.get_session(user_id)
        
        assert result is not None
        assert result['username'] == 'testuser'
    
    def test_delete_user_session(self, redis_service):
        """Test deleting user session (logout)"""
        user_id = 100
        session_data = {'username': 'testuser'}
        
        redis_service.cache_session(user_id, session_data)
        redis_service.delete_session(user_id)
        
        result = redis_service.get_session(user_id)
        assert result is None


class TestAlerts:
    """Test alert caching"""
    
    def test_add_alert(self, redis_service):
        """Test adding alert to device"""
        device_id = 1
        alert = {
            'type': 'threshold_exceeded',
            'message': 'Temperature too high',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        result = redis_service.add_alert(device_id, alert)
        assert result is True
    
    def test_get_device_alerts(self, redis_service):
        """Test getting device alerts"""
        device_id = 1
        alert = {'type': 'threshold_exceeded', 'message': 'Test alert'}
        
        redis_service.add_alert(device_id, alert)
        result = redis_service.get_alerts(device_id)
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_clear_device_alerts(self, redis_service):
        """Test clearing device alerts"""
        device_id = 1
        alert = {'type': 'test', 'message': 'Test'}
        
        redis_service.add_alert(device_id, alert)
        redis_service.clear_alerts(device_id)
        
        result = redis_service.get_alerts(device_id)
        assert len(result) == 0
    
    def test_alert_ttl(self, redis_service):
        """Test alert expiration with TTL"""
        device_id = 1
        alert = {'type': 'test'}
        
        redis_service.add_alert(device_id, alert, ttl=1)
        time.sleep(2)
        
        result = redis_service.get_alerts(device_id)
        assert len(result) == 0


class TestPubSub:
    """Test Pub/Sub functionality"""
    
    def test_publish_telemetry_event(self, redis_service):
        """Test publishing telemetry event"""
        device_id = 1
        data = {'temperature': 23.5}
        
        result = redis_service.publish_telemetry(device_id, data)
        assert result >= 0  # Returns number of subscribers
    
    def test_publish_device_status_event(self, redis_service):
        """Test publishing device status change"""
        device_id = 1
        status = 'online'
        
        result = redis_service.publish_device_status(device_id, status)
        assert result >= 0
    
    def test_publish_alert_event(self, redis_service):
        """Test publishing alert event"""
        device_id = 1
        alert = {'type': 'threshold_exceeded'}
        
        result = redis_service.publish_alert(device_id, alert)
        assert result >= 0
    
    def test_subscribe_to_device(self, redis_service):
        """Test subscribing to device channel"""
        device_id = 1
        
        pubsub = redis_service.subscribe_to_device(device_id)
        assert pubsub is not None


class TestStatistics:
    """Test statistics and metrics caching"""
    
    def test_increment_counter(self, redis_service):
        """Test incrementing a counter"""
        key = 'telemetry:count'
        
        result = redis_service.increment(key)
        assert result == 1
        
        result = redis_service.increment(key)
        assert result == 2
    
    def test_get_counter(self, redis_service):
        """Test getting counter value"""
        key = 'telemetry:count'
        
        redis_service.increment(key)
        redis_service.increment(key)
        
        result = redis_service.get_counter(key)
        assert result == 2
    
    def test_set_gauge(self, redis_service):
        """Test setting gauge metric"""
        key = 'devices:online'
        value = 42
        
        result = redis_service.set_gauge(key, value)
        assert result is True
        
        retrieved = redis_service.get_gauge(key)
        assert retrieved == 42


class TestBulkOperations:
    """Test bulk operations"""
    
    def test_bulk_cache_devices(self, redis_service):
        """Test caching multiple devices at once"""
        devices = {
            1: {'id': 1, 'name': 'Device 1'},
            2: {'id': 2, 'name': 'Device 2'},
            3: {'id': 3, 'name': 'Device 3'}
        }
        
        result = redis_service.bulk_cache_devices(devices)
        assert result is True
        
        # Verify all cached
        for device_id in devices:
            cached = redis_service.get_device(device_id)
            assert cached is not None
    
    def test_bulk_delete(self, redis_service):
        """Test deleting multiple keys"""
        keys = ['device:1', 'device:2', 'device:3']
        
        # Set some data
        for key in keys:
            redis_service.client.set(key, 'test')
        
        # Bulk delete
        result = redis_service.bulk_delete(keys)
        assert result is True


class TestCacheInvalidation:
    """Test cache invalidation strategies"""
    
    def test_invalidate_device_cache(self, redis_service):
        """Test invalidating all device-related cache"""
        device_id = 1
        
        # Cache various device data
        redis_service.cache_device(device_id, {'id': device_id})
        redis_service.cache_latest_telemetry(device_id, {'temp': 23.5})
        redis_service.set_device_online(device_id)
        
        # Invalidate all
        result = redis_service.invalidate_device_cache(device_id)
        assert result is True
        
        # Verify all cleared
        assert redis_service.get_device(device_id) is None
        assert redis_service.get_latest_telemetry(device_id) is None
    
    def test_invalidate_user_cache(self, redis_service):
        """Test invalidating user-related cache"""
        user_id = 100
        
        redis_service.cache_session(user_id, {'username': 'test'})
        redis_service.invalidate_user_cache(user_id)
        
        assert redis_service.get_session(user_id) is None


class TestErrorHandling:
    """Test error handling"""
    
    def test_handle_connection_error(self, redis_service):
        """Test handling connection errors"""
        # Verify error handling method exists
        assert hasattr(redis_service, 'handle_connection_error')
    
    def test_cache_with_invalid_data(self, redis_service):
        """Test caching with invalid data types"""
        device_id = 1
        
        # Try to cache non-serializable data
        result = redis_service.cache_device(device_id, {'func': lambda x: x})
        assert result is False
    
    def test_get_nonexistent_key(self, redis_service):
        """Test getting non-existent key"""
        result = redis_service.get_device(99999)
        assert result is None


class TestPerformance:
    """Test performance characteristics"""
    
    def test_cache_write_performance(self, redis_service):
        """Test cache write performance"""
        start_time = time.time()
        
        for i in range(1000):
            redis_service.cache_device(i, {'id': i, 'name': f'Device {i}'})
        
        elapsed = time.time() - start_time
        
        # Should be very fast (< 1 second for 1000 writes)
        assert elapsed < 1.0
    
    def test_cache_read_performance(self, redis_service):
        """Test cache read performance"""
        # Write some data
        for i in range(100):
            redis_service.cache_device(i, {'id': i})
        
        # Read it back
        start_time = time.time()
        for i in range(100):
            redis_service.get_device(i)
        elapsed = time.time() - start_time
        
        # Should be very fast
        assert elapsed < 0.5


class TestTTLManagement:
    """Test TTL (Time To Live) management"""
    
    def test_set_ttl(self, redis_service):
        """Test setting TTL on key"""
        key = 'test:key'
        redis_service.client.set(key, 'value')
        
        result = redis_service.set_ttl(key, 60)
        assert result is True
    
    def test_get_ttl(self, redis_service):
        """Test getting TTL of key"""
        key = 'test:key'
        redis_service.client.setex(key, 60, 'value')
        
        ttl = redis_service.get_ttl(key)
        assert ttl > 0 and ttl <= 60
    
    def test_persist_key(self, redis_service):
        """Test removing TTL from key"""
        key = 'test:key'
        redis_service.client.setex(key, 60, 'value')
        
        result = redis_service.persist(key)
        assert result is True
        
        ttl = redis_service.get_ttl(key)
        assert ttl == -1  # No expiration
