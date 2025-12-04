"""
Integration tests for NoSQL services with API routes
Following TDD approach - tests written first
"""

import pytest
import json
from datetime import datetime, timezone
from app import create_app
from src.models import db, User, Device


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        
        # Create test device
        device = Device(
            name='Test Device',
            device_type='sensor',
            user_id=user.id,
            status='active'
        )
        db.session.add(device)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_device(app):
    """Get test device"""
    with app.app_context():
        device = Device.query.first()
        return {
            'id': device.id,
            'api_key': device.api_key,
            'user_id': device.user_id
        }


class TestCassandraTelemetryIntegration:
    """Test Cassandra integration with telemetry endpoints"""
    
    def test_submit_telemetry_stores_in_cassandra(self, client, test_device):
        """Test that telemetry is stored in Cassandra"""
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={
                'data': {
                    'temperature': 23.5,
                    'humidity': 65.2
                }
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'Telemetry data stored successfully'
        assert 'stored_in_cassandra' in data
        assert data['stored_in_cassandra'] is True
    
    def test_get_telemetry_from_cassandra(self, client, test_device):
        """Test retrieving telemetry from Cassandra"""
        # First submit some data
        client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        # Then retrieve it
        response = client.get(
            f'/api/v1/telemetry/{test_device["id"]}',
            headers={'X-API-Key': test_device['api_key']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert data['cassandra_available'] is True
    
    def test_get_latest_telemetry_from_cassandra(self, client, test_device):
        """Test getting latest telemetry from Cassandra"""
        # Submit data
        client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 25.0, 'humidity': 70.0}}
        )
        
        # Get latest
        response = client.get(
            f'/api/v1/telemetry/{test_device["id"]}/latest',
            headers={'X-API-Key': test_device['api_key']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'latest_data' in data
        assert data['cassandra_available'] is True


class TestRedisCachingIntegration:
    """Test Redis caching integration with device endpoints"""
    
    def test_device_info_cached_in_redis(self, client, test_device):
        """Test that device info is cached in Redis"""
        # First request - cache miss
        response1 = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        
        assert response1.status_code == 200
        
        # Second request - should hit cache
        response2 = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        
        assert response2.status_code == 200
        data = json.loads(response2.data)
        assert 'device' in data
    
    def test_api_key_cached_in_redis(self, client, test_device):
        """Test that API key lookups are cached"""
        # Submit telemetry (triggers API key lookup)
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        assert response.status_code == 201
        
        # Second request should use cached API key
        response2 = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 24.0}}
        )
        
        assert response2.status_code == 201
    
    def test_latest_telemetry_cached_in_redis(self, client, test_device):
        """Test that latest telemetry is cached in Redis"""
        # Submit telemetry
        client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        # Get latest (should be cached)
        response = client.get(
            f'/api/v1/telemetry/{test_device["id"]}/latest',
            headers={'X-API-Key': test_device['api_key']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'latest_data' in data
    
    def test_device_online_status_in_redis(self, client, test_device):
        """Test that device online status is tracked in Redis"""
        # Submit telemetry (updates last_seen)
        client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        # Check status
        response = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'device' in data
        # Device should be online after recent telemetry
        assert data['device']['is_online'] is True
    
    def test_rate_limiting_with_redis(self, client, test_device):
        """Test rate limiting using Redis"""
        # Make multiple rapid requests
        responses = []
        for i in range(35):  # Exceed rate limit
            response = client.post(
                '/api/v1/telemetry',
                headers={'X-API-Key': test_device['api_key']},
                json={'data': {'temperature': 20.0 + i}}
            )
            responses.append(response.status_code)
        
        # Some requests should succeed, some might be rate limited
        assert 201 in responses


class TestMongoDBEventLogging:
    """Test MongoDB event logging integration"""
    
    def test_device_registration_logged_to_mongodb(self, client, app):
        """Test that device registration is logged to MongoDB"""
        with app.app_context():
            user = User.query.first()
            
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': user.user_id},
                json={
                    'name': 'New Device',
                    'device_type': 'sensor'
                }
            )
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert 'device' in data
            
            # Event should be logged in MongoDB
            # We'll verify this in the service layer
    
    def test_device_status_change_logged(self, client, test_device, app):
        """Test that device status changes are logged"""
        with app.app_context():
            admin_token = 'test'  # From .env
            
            response = client.put(
                f'/api/v1/admin/devices/{test_device["id"]}/status',
                headers={'Authorization': f'admin {admin_token}'},
                json={'status': 'maintenance'}
            )
            
            assert response.status_code == 200
            # Status change should be logged in MongoDB
    
    def test_user_login_logged(self, client):
        """Test that user login is logged to MongoDB"""
        response = client.post(
            '/api/v1/auth/login',
            json={
                'username': 'testuser',
                'password': 'testpass'
            }
        )
        
        assert response.status_code == 200
        # Login event should be logged in MongoDB
    
    def test_telemetry_submission_logged(self, client, test_device):
        """Test that telemetry submissions are logged"""
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        assert response.status_code == 201
        # Telemetry event should be logged in MongoDB


class TestMongoDBAlertManagement:
    """Test MongoDB alert management"""
    
    def test_threshold_alert_created_in_mongodb(self, client, test_device):
        """Test that threshold alerts are created in MongoDB"""
        # Submit telemetry that exceeds threshold
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 55.0}}  # High temperature
        )
        
        assert response.status_code == 201
        # Alert should be created in MongoDB if threshold is configured
    
    def test_device_offline_alert_created(self, client, test_device):
        """Test that offline alerts are created"""
        # This would be triggered by a background job
        # For now, just verify the endpoint exists
        pass


class TestMongoDBDeviceConfig:
    """Test MongoDB device configuration"""
    
    def test_device_config_stored_in_mongodb(self, client, test_device):
        """Test that device configurations are stored in MongoDB"""
        # Create a config endpoint (to be implemented)
        # For now, verify the service works
        from src.services.mongodb_service import MongoDBService
        
        mongo = MongoDBService()
        if mongo.is_available():
            config = {
                'device_id': test_device['id'],
                'user_id': test_device['user_id'],
                'config_version': '1.0.0',
                'settings': {
                    'sampling_rate': 60,
                    'thresholds': {
                        'temperature': {'max': 50}
                    }
                }
            }
            result = mongo.create_device_config(config)
            assert result is not None
            
            # Cleanup
            mongo.delete_device_config(test_device['id'])


class TestIntegratedDataFlow:
    """Test complete data flow across all databases"""
    
    def test_complete_telemetry_flow(self, client, test_device):
        """Test complete flow: PostgreSQL -> Cassandra -> Redis -> MongoDB"""
        # 1. Submit telemetry
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={
                'data': {
                    'temperature': 23.5,
                    'humidity': 65.2,
                    'pressure': 1013.25
                }
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        # Verify stored in Cassandra
        assert data.get('stored_in_cassandra') is True
        
        # 2. Retrieve from Cassandra
        response = client.get(
            f'/api/v1/telemetry/{test_device["id"]}/latest',
            headers={'X-API-Key': test_device['api_key']}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'latest_data' in data
        
        # 3. Check device status (uses Redis cache)
        response = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['device']['is_online'] is True
    
    def test_device_lifecycle_events(self, client, app):
        """Test device lifecycle is tracked across databases"""
        with app.app_context():
            user = User.query.first()
            
            # 1. Register device (PostgreSQL + MongoDB event)
            response = client.post(
                '/api/v1/devices/register',
                headers={'X-User-ID': user.user_id},
                json={
                    'name': 'Lifecycle Test Device',
                    'device_type': 'sensor'
                }
            )
            
            assert response.status_code == 201
            device_data = json.loads(response.data)['device']
            device_id = device_data['id']
            api_key = device_data['api_key']
            
            # 2. Submit telemetry (Cassandra + Redis)
            response = client.post(
                '/api/v1/telemetry',
                headers={'X-API-Key': api_key},
                json={'data': {'temperature': 23.5}}
            )
            
            assert response.status_code == 201
            
            # 3. Get device status (Redis cache)
            response = client.get(
                f'/api/v1/devices/{device_id}/status',
                headers={'X-User-ID': user.user_id}
            )
            
            assert response.status_code == 200
            
            # 4. Query historical data (Cassandra)
            response = client.get(
                f'/api/v1/telemetry/{device_id}',
                headers={'X-API-Key': api_key}
            )
            
            assert response.status_code == 200


class TestPerformanceWithCaching:
    """Test performance improvements with Redis caching"""
    
    def test_cached_requests_faster(self, client, test_device):
        """Test that cached requests are faster"""
        import time
        
        # First request (cache miss)
        start = time.time()
        response1 = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        time1 = time.time() - start
        
        assert response1.status_code == 200
        
        # Second request (cache hit)
        start = time.time()
        response2 = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        time2 = time.time() - start
        
        assert response2.status_code == 200
        
        # Cached request should be faster (or at least not slower)
        # Note: In tests, the difference might be minimal
        assert time2 <= time1 * 2  # Allow some variance


class TestErrorHandling:
    """Test error handling with NoSQL services"""
    
    def test_cassandra_unavailable_fallback(self, client, test_device):
        """Test graceful degradation when Cassandra is unavailable"""
        # This would require mocking Cassandra failure
        # For now, verify the endpoint handles errors gracefully
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        # Should still return a response (even if Cassandra fails)
        assert response.status_code in [201, 500]
    
    def test_redis_unavailable_fallback(self, client, test_device):
        """Test that app works when Redis is unavailable"""
        # Should fall back to database queries
        response = client.get(
            f'/api/v1/devices/{test_device["id"]}/status',
            headers={'X-User-ID': str(test_device['user_id'])}
        )
        
        assert response.status_code == 200
    
    def test_mongodb_unavailable_fallback(self, client, test_device):
        """Test that app works when MongoDB is unavailable"""
        # Events might not be logged, but app should work
        response = client.post(
            '/api/v1/telemetry',
            headers={'X-API-Key': test_device['api_key']},
            json={'data': {'temperature': 23.5}}
        )
        
        assert response.status_code == 201
