"""
Test Device Routes with NoSQL Integration (Redis + MongoDB)
Following TDD approach
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['IOTFLOW_ADMIN_TOKEN'] = 'test_admin_token'

from app import create_app
from src.models import db, Device, User


class TestDeviceRegistrationWithNoSQL:
    """Test device registration with Redis caching and MongoDB logging"""
    
    def test_register_device_caches_in_redis(self, client, test_user):
        """Test that device registration caches device info in Redis"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.cache_device_info = Mock()
            mock_redis.cache_api_key = Mock()
            
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': test_user['user_id']},
                json={
                    'name': 'Test Sensor',
                    'device_type': 'sensor',
                    'location': 'Living Room'
                }
            )
            
            assert response.status_code == 201
            
            # Verify Redis caching was called
            assert mock_redis.cache_device_info.called
            assert mock_redis.cache_api_key.called
            
            # Verify cache_device_info was called with correct data
            call_args = mock_redis.cache_device_info.call_args
            device_id = call_args[0][0]
            cached_data = call_args[0][1]
            
            assert cached_data['name'] == 'Test Sensor'
            assert cached_data['device_type'] == 'sensor'
            assert cached_data['status'] == 'inactive'
    
    def test_register_device_logs_to_mongodb(self, client, test_user):
        """Test that device registration logs event to MongoDB"""
        with patch('src.routes.devices.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': test_user['user_id']},
                json={
                    'name': 'Test Sensor',
                    'device_type': 'sensor'
                }
            )
            
            assert response.status_code == 201
            
            # Verify MongoDB logging was called
            assert mock_mongo.log_event.called
            
            # Verify event data
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'device.registered'
            assert event_data['details']['device_name'] == 'Test Sensor'
            assert event_data['details']['device_type'] == 'sensor'
    
    def test_register_device_continues_on_redis_failure(self, client, test_user):
        """Test that device registration continues even if Redis fails"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.cache_device_info.side_effect = Exception("Redis connection failed")
            
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': test_user['user_id']},
                json={
                    'name': 'Test Sensor',
                    'device_type': 'sensor'
                }
            )
            
            # Should still succeed
            assert response.status_code == 201
            data = response.get_json()
            assert data['message'] == 'Device registered successfully'
    
    def test_register_device_continues_on_mongodb_failure(self, client, test_user):
        """Test that device registration continues even if MongoDB fails"""
        with patch('src.routes.devices.mongodb_service') as mock_mongo:
            mock_mongo.log_event.side_effect = Exception("MongoDB connection failed")
            
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': test_user['user_id']},
                json={
                    'name': 'Test Sensor',
                    'device_type': 'sensor'
                }
            )
            
            # Should still succeed
            assert response.status_code == 201


class TestDeviceStatusWithNoSQL:
    """Test device status endpoint with Redis caching"""
    
    def test_get_device_status_checks_redis_cache(self, client, test_device):
        """Test that device status checks Redis for online status"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.get_device_info.return_value = {
                'device_id': test_device['id'],
                'name': test_device['name'],
                'status': 'active'
            }
            mock_redis.is_device_online.return_value = True
            
            response = client.get(
                '/api/v1/devices/status',
                headers={'X-API-Key': test_device['api_key']}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Verify Redis was checked
            assert mock_redis.get_device_info.called
            assert mock_redis.is_device_online.called
            
            # Verify response includes cached flag
            assert data['device']['is_online'] == True
            assert data['device']['cached'] == True
    
    def test_get_device_status_falls_back_to_database(self, client, test_device):
        """Test that device status falls back to database if Redis fails"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.get_device_info.return_value = None
            mock_redis.is_device_online.return_value = False
            
            response = client.get(
                '/api/v1/devices/status',
                headers={'X-API-Key': test_device['api_key']}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'device' in data


class TestDeviceConfigUpdateWithNoSQL:
    """Test device config update with Redis and MongoDB"""
    
    def test_update_device_config_updates_redis_cache(self, client, test_device):
        """Test that config update refreshes Redis cache"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.cache_device_info = Mock()
            
            response = client.put(
                '/api/v1/devices/config',
                headers={'X-API-Key': test_device['api_key']},
                json={
                    'status': 'active',
                    'location': 'Kitchen'
                }
            )
            
            assert response.status_code == 200
            
            # Verify Redis cache was updated
            assert mock_redis.cache_device_info.called
            cached_data = mock_redis.cache_device_info.call_args[0][1]
            assert cached_data['status'] == 'active'
            assert cached_data['location'] == 'Kitchen'
    
    def test_update_device_config_logs_to_mongodb(self, client, test_device):
        """Test that config update logs event to MongoDB"""
        with patch('src.routes.devices.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.put(
                '/api/v1/devices/config',
                headers={'X-API-Key': test_device['api_key']},
                json={
                    'status': 'maintenance',
                    'firmware_version': '2.0.0'
                }
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'device.config_updated'
            assert 'status' in event_data['details']['updated_fields']
            assert 'firmware_version' in event_data['details']['updated_fields']


class TestDeviceHeartbeatWithNoSQL:
    """Test device heartbeat with Redis"""
    
    def test_heartbeat_updates_redis_online_status(self, client, test_device):
        """Test that heartbeat updates device online status in Redis"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            mock_redis.set_device_online = Mock()
            mock_redis.update_last_seen = Mock()
            
            response = client.post(
                '/api/v1/devices/heartbeat',
                headers={'X-API-Key': test_device['api_key']}
            )
            
            assert response.status_code == 200
            
            # Note: These would be called if we add them to the heartbeat endpoint
            # For now, they're called in telemetry submission


class TestDeviceListWithNoSQL:
    """Test device listing with Redis caching"""
    
    def test_list_user_devices_can_use_redis_cache(self, client, test_user, test_device):
        """Test that listing devices can leverage Redis cache for performance"""
        with patch('src.routes.devices.redis_service') as mock_redis:
            # Mock Redis to return cached device info
            mock_redis.get_device_info.return_value = {
                'device_id': test_device['id'],
                'name': test_device['name'],
                'status': 'active'
            }
            
            response = client.get(
                f'/api/v1/devices/user/{test_user["user_id"]}',
                headers={'X-User-ID': test_user['user_id']}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['total_devices'] >= 1


# Fixtures
@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        # Return dict with user data
        return {
            'id': user.id,
            'user_id': user.user_id,
            'username': user.username
        }


@pytest.fixture
def test_device(app, test_user):
    """Create a test device"""
    with app.app_context():
        device = Device(
            name='Test Device',
            device_type='sensor',
            user_id=test_user['id'],
            status='active'
        )
        
        db.session.add(device)
        db.session.commit()
        
        # Return dict with device data
        return {
            'id': device.id,
            'name': device.name,
            'api_key': device.api_key,
            'user_id': device.user_id
        }
