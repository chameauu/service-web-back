"""
Redis Cache Service
Handles caching, sessions, and real-time data
"""

import logging
import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import redis
from redis.exceptions import RedisError, ConnectionError

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Service for managing cache and real-time data in Redis"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', '6379'))
        self.password = os.getenv('REDIS_PASSWORD', 'iotflowpass')
        self.db = int(os.getenv('REDIS_DB', '0'))
        
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Redis"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis not available: {e}")
            return False
    
    def ping(self) -> bool:
        """Ping Redis"""
        try:
            return self.client.ping()
        except:
            return False
    
    # Device Caching
    
    def cache_device(self, device_id: int, device_data: Dict, ttl: int = 3600) -> bool:
        """Cache device information"""
        try:
            key = f"device:{device_id}"
            self.client.setex(key, ttl, json.dumps(device_data))
            return True
        except Exception as e:
            logger.error(f"Error caching device: {e}")
            return False
    
    def get_device(self, device_id: int) -> Optional[Dict]:
        """Get cached device"""
        try:
            key = f"device:{device_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None
    
    def delete_device(self, device_id: int) -> bool:
        """Delete device from cache"""
        try:
            key = f"device:{device_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting device: {e}")
            return False
    
    # API Key Caching
    
    def cache_api_key(self, api_key: str, device_data: Dict, ttl: int = 3600) -> bool:
        """Cache API key to device mapping"""
        try:
            key = f"apikey:{api_key}"
            self.client.setex(key, ttl, json.dumps(device_data))
            return True
        except Exception as e:
            logger.error(f"Error caching API key: {e}")
            return False
    
    def get_device_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get device by API key"""
        try:
            key = f"apikey:{api_key}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting device by API key: {e}")
            return None
    
    def invalidate_api_key(self, api_key: str) -> bool:
        """Invalidate API key cache"""
        try:
            key = f"apikey:{api_key}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error invalidating API key: {e}")
            return False
    
    # Device Status
    
    def set_device_online(self, device_id: int) -> bool:
        """Mark device as online"""
        try:
            timestamp = time.time()
            self.client.zadd("devices:online", {device_id: timestamp})
            self.update_last_seen(device_id)
            return True
        except Exception as e:
            logger.error(f"Error setting device online: {e}")
            return False
    
    def set_device_offline(self, device_id: int) -> bool:
        """Mark device as offline"""
        try:
            self.client.zrem("devices:online", device_id)
            return True
        except Exception as e:
            logger.error(f"Error setting device offline: {e}")
            return False
    
    def is_device_online(self, device_id: int) -> bool:
        """Check if device is online"""
        try:
            score = self.client.zscore("devices:online", device_id)
            if not score:
                return False
            # Check if last seen was within 5 minutes
            return (time.time() - score) < 300
        except Exception as e:
            logger.error(f"Error checking device online: {e}")
            return False
    
    def get_online_devices(self) -> List[int]:
        """Get list of online devices"""
        try:
            now = time.time()
            cutoff = now - 300  # 5 minutes ago
            devices = self.client.zrangebyscore("devices:online", cutoff, now)
            return [int(d) for d in devices]
        except Exception as e:
            logger.error(f"Error getting online devices: {e}")
            return []
    
    def update_last_seen(self, device_id: int) -> bool:
        """Update device last seen timestamp"""
        try:
            key = f"device:lastseen:{device_id}"
            self.client.set(key, datetime.now(timezone.utc).isoformat())
            return True
        except Exception as e:
            logger.error(f"Error updating last seen: {e}")
            return False
    
    def get_last_seen(self, device_id: int) -> Optional[str]:
        """Get device last seen timestamp"""
        try:
            key = f"device:lastseen:{device_id}"
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting last seen: {e}")
            return None
    
    # Latest Telemetry
    
    def cache_latest_telemetry(self, device_id: int, telemetry: Dict, ttl: int = 600) -> bool:
        """Cache latest telemetry values"""
        try:
            key = f"telemetry:latest:{device_id}"
            self.client.hset(key, mapping=telemetry)
            self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Error caching latest telemetry: {e}")
            return False
    
    def get_latest_telemetry(self, device_id: int) -> Optional[Dict]:
        """Get latest telemetry"""
        try:
            key = f"telemetry:latest:{device_id}"
            data = self.client.hgetall(key)
            if not data:
                return None
            # Convert string values back to float
            return {k: float(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error getting latest telemetry: {e}")
            return None
    
    def update_measurement(self, device_id: int, measurement_name: str, value: float) -> bool:
        """Update a single measurement"""
        try:
            key = f"telemetry:latest:{device_id}"
            self.client.hset(key, measurement_name, value)
            return True
        except Exception as e:
            logger.error(f"Error updating measurement: {e}")
            return False
    
    def get_measurement(self, device_id: int, measurement_name: str) -> Optional[float]:
        """Get specific measurement value"""
        try:
            key = f"telemetry:latest:{device_id}"
            value = self.client.hget(key, measurement_name)
            return float(value) if value else None
        except Exception as e:
            logger.error(f"Error getting measurement: {e}")
            return None
    
    # Rate Limiting
    
    def check_rate_limit(self, key: str, max_requests: int, window: int) -> bool:
        """Check if rate limit is exceeded"""
        try:
            rate_key = f"ratelimit:{key}"
            current = self.client.get(rate_key)
            
            if current is None:
                # First request in window
                self.client.setex(rate_key, window, 1)
                return True
            
            count = int(current)
            if count >= max_requests:
                return False
            
            # Increment counter
            self.client.incr(rate_key)
            return True
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def get_rate_limit_remaining(self, key: str, max_requests: int) -> int:
        """Get remaining rate limit"""
        try:
            rate_key = f"ratelimit:{key}"
            current = self.client.get(rate_key)
            if current is None:
                return max_requests
            return max(0, max_requests - int(current))
        except Exception as e:
            logger.error(f"Error getting rate limit remaining: {e}")
            return max_requests
    
    # Session Management
    
    def cache_session(self, user_id: int, session_data: Dict, ttl: int = 1800) -> bool:
        """Cache user session"""
        try:
            key = f"session:{user_id}"
            self.client.setex(key, ttl, json.dumps(session_data))
            return True
        except Exception as e:
            logger.error(f"Error caching session: {e}")
            return False
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get user session"""
        try:
            key = f"session:{user_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    def delete_session(self, user_id: int) -> bool:
        """Delete user session (logout)"""
        try:
            key = f"session:{user_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
    
    # Alerts
    
    def add_alert(self, device_id: int, alert: Dict, ttl: int = 86400) -> bool:
        """Add alert to device"""
        try:
            key = f"alerts:{device_id}"
            self.client.rpush(key, json.dumps(alert))
            self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Error adding alert: {e}")
            return False
    
    def get_alerts(self, device_id: int) -> List[Dict]:
        """Get device alerts"""
        try:
            key = f"alerts:{device_id}"
            alerts = self.client.lrange(key, 0, -1)
            return [json.loads(a) for a in alerts]
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def clear_alerts(self, device_id: int) -> bool:
        """Clear device alerts"""
        try:
            key = f"alerts:{device_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing alerts: {e}")
            return False
    
    # Pub/Sub
    
    def publish_telemetry(self, device_id: int, data: Dict) -> int:
        """Publish telemetry event"""
        try:
            channel = f"device:{device_id}:telemetry"
            return self.client.publish(channel, json.dumps(data))
        except Exception as e:
            logger.error(f"Error publishing telemetry: {e}")
            return 0
    
    def publish_device_status(self, device_id: int, status: str) -> int:
        """Publish device status change"""
        try:
            channel = f"device:{device_id}:status"
            return self.client.publish(channel, status)
        except Exception as e:
            logger.error(f"Error publishing device status: {e}")
            return 0
    
    def publish_alert(self, device_id: int, alert: Dict) -> int:
        """Publish alert event"""
        try:
            channel = f"device:{device_id}:alert"
            return self.client.publish(channel, json.dumps(alert))
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
            return 0
    
    def subscribe_to_device(self, device_id: int):
        """Subscribe to device channel"""
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(f"device:{device_id}:telemetry")
            return pubsub
        except Exception as e:
            logger.error(f"Error subscribing to device: {e}")
            return None
    
    # Statistics
    
    def increment(self, key: str) -> int:
        """Increment counter"""
        try:
            return self.client.incr(key)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0
    
    def get_counter(self, key: str) -> int:
        """Get counter value"""
        try:
            value = self.client.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Error getting counter: {e}")
            return 0
    
    def set_gauge(self, key: str, value: int) -> bool:
        """Set gauge metric"""
        try:
            self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Error setting gauge: {e}")
            return False
    
    def get_gauge(self, key: str) -> Optional[int]:
        """Get gauge value"""
        try:
            value = self.client.get(key)
            return int(value) if value else None
        except Exception as e:
            logger.error(f"Error getting gauge: {e}")
            return None
    
    # Bulk Operations
    
    def bulk_cache_devices(self, devices: Dict[int, Dict]) -> bool:
        """Cache multiple devices at once"""
        try:
            pipe = self.client.pipeline()
            for device_id, device_data in devices.items():
                key = f"device:{device_id}"
                pipe.set(key, json.dumps(device_data))
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Error bulk caching devices: {e}")
            return False
    
    def bulk_delete(self, keys: List[str]) -> bool:
        """Delete multiple keys"""
        try:
            if keys:
                self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Error bulk deleting: {e}")
            return False
    
    # Cache Invalidation
    
    def invalidate_device_cache(self, device_id: int) -> bool:
        """Invalidate all device-related cache"""
        try:
            keys = [
                f"device:{device_id}",
                f"telemetry:latest:{device_id}",
                f"device:lastseen:{device_id}",
                f"alerts:{device_id}"
            ]
            self.client.delete(*keys)
            self.client.zrem("devices:online", device_id)
            return True
        except Exception as e:
            logger.error(f"Error invalidating device cache: {e}")
            return False
    
    def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate user-related cache"""
        try:
            key = f"session:{user_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")
            return False
    
    # TTL Management
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        """Set TTL on key"""
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Error setting TTL: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get TTL of key"""
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL: {e}")
            return -1
    
    def persist(self, key: str) -> bool:
        """Remove TTL from key"""
        try:
            return self.client.persist(key)
        except Exception as e:
            logger.error(f"Error persisting key: {e}")
            return False
    
    # Error Handling
    
    def handle_connection_error(self):
        """Handle connection errors"""
        logger.error("Redis connection error")
        self._connect()
    
    # Test Utilities
    
    def flush_test_data(self):
        """Flush test data"""
        try:
            self.client.flushdb()
        except Exception as e:
            logger.error(f"Error flushing test data: {e}")
    
    def close(self):
        """Close connection"""
        if self.client:
            self.client.close()
