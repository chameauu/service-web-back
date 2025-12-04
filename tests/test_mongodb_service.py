"""
Test suite for MongoDB Service
Following TDD approach - tests written first
"""

import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from src.services.mongodb_service import MongoDBService


@pytest.fixture
def mongodb_service():
    """Fixture to create MongoDB service instance"""
    service = MongoDBService()
    yield service
    # Cleanup after tests
    if service.is_available():
        service.cleanup_test_data()


class TestMongoDBConnection:
    """Test MongoDB connection and availability"""
    
    def test_mongodb_is_available(self, mongodb_service):
        """Test that MongoDB service is available"""
        assert mongodb_service.is_available() is True
    
    def test_mongodb_client_exists(self, mongodb_service):
        """Test that MongoDB client is created"""
        assert mongodb_service.client is not None
    
    def test_database_exists(self, mongodb_service):
        """Test that database is accessible"""
        assert mongodb_service.db is not None


class TestDeviceConfigs:
    """Test device configuration management"""
    
    def test_create_device_config(self, mongodb_service):
        """Test creating device configuration"""
        config = {
            'device_id': 1,
            'user_id': 100,
            'config_version': '1.0.0',
            'settings': {
                'sampling_rate': 60,
                'thresholds': {
                    'temperature': {'min': 0, 'max': 50}
                }
            }
        }
        
        result = mongodb_service.create_device_config(config)
        assert result is not None
        assert 'config_id' in result
    
    def test_get_device_config(self, mongodb_service):
        """Test retrieving device configuration"""
        config = {
            'device_id': 1,
            'user_id': 100,
            'config_version': '1.0.0',
            'settings': {'sampling_rate': 60}
        }
        
        created = mongodb_service.create_device_config(config)
        retrieved = mongodb_service.get_device_config(device_id=1)
        
        assert retrieved is not None
        assert retrieved['device_id'] == 1
        assert retrieved['settings']['sampling_rate'] == 60
    
    def test_update_device_config(self, mongodb_service):
        """Test updating device configuration"""
        config = {
            'device_id': 1,
            'user_id': 100,
            'config_version': '1.0.0',
            'settings': {'sampling_rate': 60}
        }
        
        mongodb_service.create_device_config(config)
        
        updates = {
            'config_version': '1.1.0',
            'settings': {'sampling_rate': 30}
        }
        
        result = mongodb_service.update_device_config(device_id=1, updates=updates)
        assert result is True
        
        updated = mongodb_service.get_device_config(device_id=1)
        assert updated['config_version'] == '1.1.0'
        assert updated['settings']['sampling_rate'] == 30
    
    def test_delete_device_config(self, mongodb_service):
        """Test deleting device configuration"""
        config = {
            'device_id': 1,
            'user_id': 100,
            'config_version': '1.0.0'
        }
        
        mongodb_service.create_device_config(config)
        result = mongodb_service.delete_device_config(device_id=1)
        
        assert result is True
        
        retrieved = mongodb_service.get_device_config(device_id=1)
        assert retrieved is None
    
    def test_get_user_configs(self, mongodb_service):
        """Test getting all configs for a user"""
        configs = [
            {'device_id': 1, 'user_id': 100, 'config_version': '1.0.0'},
            {'device_id': 2, 'user_id': 100, 'config_version': '1.0.0'},
            {'device_id': 3, 'user_id': 200, 'config_version': '1.0.0'}
        ]
        
        for config in configs:
            mongodb_service.create_device_config(config)
        
        user_configs = mongodb_service.get_user_configs(user_id=100)
        
        assert len(user_configs) == 2


class TestEventLogs:
    """Test event logging"""
    
    def test_log_event(self, mongodb_service):
        """Test logging an event"""
        event = {
            'event_type': 'device.status_changed',
            'device_id': 1,
            'user_id': 100,
            'details': {
                'old_status': 'active',
                'new_status': 'maintenance'
            }
        }
        
        result = mongodb_service.log_event(event)
        assert result is not None
        assert 'event_id' in result
    
    def test_get_device_events(self, mongodb_service):
        """Test retrieving device events"""
        event = {
            'event_type': 'device.registered',
            'device_id': 1,
            'user_id': 100
        }
        
        mongodb_service.log_event(event)
        events = mongodb_service.get_device_events(device_id=1)
        
        assert isinstance(events, list)
        assert len(events) > 0
        assert events[0]['device_id'] == 1
    
    def test_get_user_events(self, mongodb_service):
        """Test retrieving user events"""
        events_data = [
            {'event_type': 'device.registered', 'device_id': 1, 'user_id': 100},
            {'event_type': 'device.updated', 'device_id': 2, 'user_id': 100}
        ]
        
        for event in events_data:
            mongodb_service.log_event(event)
        
        user_events = mongodb_service.get_user_events(user_id=100)
        
        assert len(user_events) >= 2
    
    def test_get_events_by_type(self, mongodb_service):
        """Test retrieving events by type"""
        events_data = [
            {'event_type': 'device.registered', 'device_id': 1},
            {'event_type': 'device.registered', 'device_id': 2},
            {'event_type': 'device.deleted', 'device_id': 3}
        ]
        
        for event in events_data:
            mongodb_service.log_event(event)
        
        registered_events = mongodb_service.get_events_by_type('device.registered')
        
        assert len(registered_events) >= 2
    
    def test_get_events_with_time_range(self, mongodb_service):
        """Test retrieving events within time range"""
        event = {
            'event_type': 'test.event',
            'device_id': 1
        }
        
        mongodb_service.log_event(event)
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        events = mongodb_service.get_events(
            start_time=start_time,
            end_time=end_time
        )
        
        assert isinstance(events, list)


class TestAlerts:
    """Test alert management"""
    
    def test_create_alert(self, mongodb_service):
        """Test creating an alert"""
        alert = {
            'device_id': 1,
            'user_id': 100,
            'alert_type': 'threshold_exceeded',
            'severity': 'warning',
            'message': 'Temperature too high',
            'details': {
                'measurement': 'temperature',
                'value': 52.3,
                'threshold': 50
            },
            'status': 'active'
        }
        
        result = mongodb_service.create_alert(alert)
        assert result is not None
        assert 'alert_id' in result
    
    def test_get_device_alerts(self, mongodb_service):
        """Test retrieving device alerts"""
        alert = {
            'device_id': 1,
            'user_id': 100,
            'alert_type': 'threshold_exceeded',
            'severity': 'warning',
            'status': 'active'
        }
        
        mongodb_service.create_alert(alert)
        alerts = mongodb_service.get_device_alerts(device_id=1)
        
        assert isinstance(alerts, list)
        assert len(alerts) > 0
    
    def test_get_active_alerts(self, mongodb_service):
        """Test retrieving active alerts"""
        alerts_data = [
            {'device_id': 1, 'alert_type': 'test', 'severity': 'info', 'status': 'active'},
            {'device_id': 2, 'alert_type': 'test', 'severity': 'info', 'status': 'resolved'}
        ]
        
        for alert in alerts_data:
            mongodb_service.create_alert(alert)
        
        active = mongodb_service.get_active_alerts()
        
        assert all(a['status'] == 'active' for a in active)
    
    def test_acknowledge_alert(self, mongodb_service):
        """Test acknowledging an alert"""
        alert = {
            'device_id': 1,
            'alert_type': 'test',
            'severity': 'warning',
            'status': 'active',
            'acknowledged': False
        }
        
        created = mongodb_service.create_alert(alert)
        alert_id = created['alert_id']
        
        result = mongodb_service.acknowledge_alert(alert_id)
        assert result is True
        
        updated = mongodb_service.get_alert(alert_id)
        assert updated['acknowledged'] is True
    
    def test_resolve_alert(self, mongodb_service):
        """Test resolving an alert"""
        alert = {
            'device_id': 1,
            'alert_type': 'test',
            'severity': 'warning',
            'status': 'active'
        }
        
        created = mongodb_service.create_alert(alert)
        alert_id = created['alert_id']
        
        result = mongodb_service.resolve_alert(alert_id)
        assert result is True
        
        updated = mongodb_service.get_alert(alert_id)
        assert updated['status'] == 'resolved'
        assert updated['resolved_at'] is not None
    
    def test_get_alerts_by_severity(self, mongodb_service):
        """Test retrieving alerts by severity"""
        alerts_data = [
            {'device_id': 1, 'alert_type': 'test', 'severity': 'critical', 'status': 'active'},
            {'device_id': 2, 'alert_type': 'test', 'severity': 'warning', 'status': 'active'}
        ]
        
        for alert in alerts_data:
            mongodb_service.create_alert(alert)
        
        critical = mongodb_service.get_alerts_by_severity('critical')
        
        assert all(a['severity'] == 'critical' for a in critical)


class TestAnalytics:
    """Test analytics and reporting"""
    
    def test_create_analytics_report(self, mongodb_service):
        """Test creating analytics report"""
        report = {
            'report_type': 'device_health',
            'device_id': 1,
            'user_id': 100,
            'period': {
                'start': datetime.now(timezone.utc) - timedelta(days=30),
                'end': datetime.now(timezone.utc)
            },
            'metrics': {
                'uptime_percentage': 99.2,
                'total_data_points': 44640,
                'average_temperature': 23.5
            }
        }
        
        result = mongodb_service.create_analytics_report(report)
        assert result is not None
        assert 'report_id' in result
    
    def test_get_device_reports(self, mongodb_service):
        """Test retrieving device reports"""
        report = {
            'report_type': 'device_health',
            'device_id': 1,
            'user_id': 100,
            'metrics': {}
        }
        
        mongodb_service.create_analytics_report(report)
        reports = mongodb_service.get_device_reports(device_id=1)
        
        assert isinstance(reports, list)
        assert len(reports) > 0
    
    def test_get_latest_report(self, mongodb_service):
        """Test getting latest report for device"""
        report = {
            'report_type': 'device_health',
            'device_id': 1,
            'metrics': {'uptime': 99.5}
        }
        
        mongodb_service.create_analytics_report(report)
        latest = mongodb_service.get_latest_report(device_id=1, report_type='device_health')
        
        assert latest is not None
        assert latest['device_id'] == 1


class TestUserPreferences:
    """Test user preferences management"""
    
    def test_create_user_preferences(self, mongodb_service):
        """Test creating user preferences"""
        preferences = {
            'user_id': 100,
            'preferences': {
                'dashboard': {
                    'default_view': 'grid',
                    'refresh_interval': 30
                },
                'notifications': {
                    'email': True,
                    'push': False
                }
            }
        }
        
        result = mongodb_service.create_user_preferences(preferences)
        assert result is not None
    
    def test_get_user_preferences(self, mongodb_service):
        """Test retrieving user preferences"""
        preferences = {
            'user_id': 100,
            'preferences': {
                'dashboard': {'default_view': 'grid'}
            }
        }
        
        mongodb_service.create_user_preferences(preferences)
        retrieved = mongodb_service.get_user_preferences(user_id=100)
        
        assert retrieved is not None
        assert retrieved['user_id'] == 100
    
    def test_update_user_preferences(self, mongodb_service):
        """Test updating user preferences"""
        preferences = {
            'user_id': 100,
            'preferences': {'theme': 'light'}
        }
        
        mongodb_service.create_user_preferences(preferences)
        
        updates = {
            'preferences': {'theme': 'dark', 'language': 'en'}
        }
        
        result = mongodb_service.update_user_preferences(user_id=100, updates=updates)
        assert result is True
        
        updated = mongodb_service.get_user_preferences(user_id=100)
        assert updated['preferences']['theme'] == 'dark'


class TestDeviceMetadata:
    """Test device metadata management"""
    
    def test_create_device_metadata(self, mongodb_service):
        """Test creating device metadata"""
        metadata = {
            'device_id': 1,
            'tags': ['production', 'critical'],
            'location': {
                'type': 'Point',
                'coordinates': [-73.935242, 40.730610]
            },
            'custom_fields': {
                'department': 'Operations',
                'cost_center': 'CC-1234'
            }
        }
        
        result = mongodb_service.create_device_metadata(metadata)
        assert result is not None
    
    def test_get_device_metadata(self, mongodb_service):
        """Test retrieving device metadata"""
        metadata = {
            'device_id': 1,
            'tags': ['production']
        }
        
        mongodb_service.create_device_metadata(metadata)
        retrieved = mongodb_service.get_device_metadata(device_id=1)
        
        assert retrieved is not None
        assert 'production' in retrieved['tags']
    
    def test_add_device_tag(self, mongodb_service):
        """Test adding tag to device"""
        metadata = {
            'device_id': 1,
            'tags': ['production']
        }
        
        mongodb_service.create_device_metadata(metadata)
        result = mongodb_service.add_device_tag(device_id=1, tag='critical')
        
        assert result is True
        
        updated = mongodb_service.get_device_metadata(device_id=1)
        assert 'critical' in updated['tags']
    
    def test_remove_device_tag(self, mongodb_service):
        """Test removing tag from device"""
        metadata = {
            'device_id': 1,
            'tags': ['production', 'critical']
        }
        
        mongodb_service.create_device_metadata(metadata)
        result = mongodb_service.remove_device_tag(device_id=1, tag='critical')
        
        assert result is True
        
        updated = mongodb_service.get_device_metadata(device_id=1)
        assert 'critical' not in updated['tags']
    
    def test_find_devices_by_tag(self, mongodb_service):
        """Test finding devices by tag"""
        metadata_list = [
            {'device_id': 1, 'tags': ['production', 'critical']},
            {'device_id': 2, 'tags': ['production']},
            {'device_id': 3, 'tags': ['development']}
        ]
        
        for metadata in metadata_list:
            mongodb_service.create_device_metadata(metadata)
        
        devices = mongodb_service.find_devices_by_tag('production')
        
        assert len(devices) >= 2
    
    def test_geospatial_query(self, mongodb_service):
        """Test geospatial query for nearby devices"""
        metadata = {
            'device_id': 1,
            'location': {
                'type': 'Point',
                'coordinates': [-73.935242, 40.730610]
            }
        }
        
        mongodb_service.create_device_metadata(metadata)
        
        # Find devices near coordinates
        nearby = mongodb_service.find_devices_near(
            longitude=-73.935242,
            latitude=40.730610,
            max_distance=1000  # meters
        )
        
        assert isinstance(nearby, list)


class TestAggregationPipeline:
    """Test MongoDB aggregation pipeline queries"""
    
    def test_aggregate_alerts_by_severity(self, mongodb_service):
        """Test aggregating alerts by severity"""
        alerts_data = [
            {'device_id': 1, 'alert_type': 'test', 'severity': 'critical', 'status': 'active'},
            {'device_id': 2, 'alert_type': 'test', 'severity': 'critical', 'status': 'active'},
            {'device_id': 3, 'alert_type': 'test', 'severity': 'warning', 'status': 'active'}
        ]
        
        for alert in alerts_data:
            mongodb_service.create_alert(alert)
        
        result = mongodb_service.aggregate_alerts_by_severity()
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_aggregate_events_by_type(self, mongodb_service):
        """Test aggregating events by type"""
        events_data = [
            {'event_type': 'device.registered', 'device_id': 1},
            {'event_type': 'device.registered', 'device_id': 2},
            {'event_type': 'device.updated', 'device_id': 3}
        ]
        
        for event in events_data:
            mongodb_service.log_event(event)
        
        result = mongodb_service.aggregate_events_by_type()
        
        assert isinstance(result, list)


class TestBulkOperations:
    """Test bulk operations"""
    
    def test_bulk_insert_events(self, mongodb_service):
        """Test bulk inserting events"""
        events = [
            {'event_type': 'test', 'device_id': i}
            for i in range(100)
        ]
        
        result = mongodb_service.bulk_insert_events(events)
        assert result is True
    
    def test_bulk_update_configs(self, mongodb_service):
        """Test bulk updating configs"""
        # Create configs
        for i in range(5):
            mongodb_service.create_device_config({
                'device_id': i,
                'user_id': 100,
                'config_version': '1.0.0'
            })
        
        # Bulk update
        updates = {'config_version': '2.0.0'}
        result = mongodb_service.bulk_update_configs(
            filter={'user_id': 100},
            updates=updates
        )
        
        assert result is True


class TestIndexes:
    """Test index creation and usage"""
    
    def test_create_indexes(self, mongodb_service):
        """Test creating indexes"""
        result = mongodb_service.create_indexes()
        assert result is True
    
    def test_list_indexes(self, mongodb_service):
        """Test listing collection indexes"""
        indexes = mongodb_service.list_indexes('device_configs')
        assert isinstance(indexes, list)


class TestErrorHandling:
    """Test error handling"""
    
    def test_handle_duplicate_key(self, mongodb_service):
        """Test handling duplicate key error"""
        config = {
            'device_id': 1,
            'user_id': 100,
            'config_version': '1.0.0'
        }
        
        mongodb_service.create_device_config(config)
        
        # Try to create duplicate
        result = mongodb_service.create_device_config(config)
        assert result is None or 'error' in result
    
    def test_handle_invalid_object_id(self, mongodb_service):
        """Test handling invalid ObjectId"""
        result = mongodb_service.get_alert('invalid_id')
        assert result is None
    
    def test_handle_connection_error(self, mongodb_service):
        """Test handling connection errors"""
        assert hasattr(mongodb_service, 'handle_connection_error')


class TestPerformance:
    """Test performance characteristics"""
    
    def test_bulk_insert_performance(self, mongodb_service):
        """Test bulk insert performance"""
        import time
        
        events = [
            {'event_type': 'test', 'device_id': i}
            for i in range(1000)
        ]
        
        start_time = time.time()
        mongodb_service.bulk_insert_events(events)
        elapsed = time.time() - start_time
        
        # Should be fast (< 2 seconds for 1000 records)
        assert elapsed < 2.0
    
    def test_query_performance(self, mongodb_service):
        """Test query performance with indexes"""
        import time
        
        # Insert test data
        for i in range(100):
            mongodb_service.create_device_config({
                'device_id': i,
                'user_id': 100,
                'config_version': '1.0.0'
            })
        
        # Query with index
        start_time = time.time()
        result = mongodb_service.get_user_configs(user_id=100)
        elapsed = time.time() - start_time
        
        # Should be fast
        assert elapsed < 0.5
        assert len(result) > 0
