"""
Test suite for Cassandra Telemetry Service
Following TDD approach - tests written first
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.services.cassandra_telemetry import CassandraTelemetryService


@pytest.fixture
def cassandra_service():
    """Fixture to create Cassandra service instance"""
    service = CassandraTelemetryService()
    yield service
    # Cleanup after tests
    if service.is_available():
        service.cleanup_test_data()


class TestCassandraConnection:
    """Test Cassandra connection and availability"""
    
    def test_cassandra_is_available(self, cassandra_service):
        """Test that Cassandra service is available"""
        assert cassandra_service.is_available() is True
    
    def test_cassandra_session_exists(self, cassandra_service):
        """Test that Cassandra session is created"""
        assert cassandra_service.session is not None
    
    def test_keyspace_exists(self, cassandra_service):
        """Test that telemetry keyspace exists"""
        result = cassandra_service.keyspace_exists('telemetry')
        assert result is True


class TestTelemetryWrite:
    """Test writing telemetry data to Cassandra"""
    
    def test_write_single_measurement(self, cassandra_service):
        """Test writing a single telemetry measurement"""
        device_id = 1
        data = {'temperature': 23.5}
        timestamp = datetime.now(timezone.utc)
        
        result = cassandra_service.write_telemetry(
            device_id=device_id,
            data=data,
            timestamp=timestamp
        )
        
        assert result is True
    
    def test_write_multiple_measurements(self, cassandra_service):
        """Test writing multiple measurements at once"""
        device_id = 1
        data = {
            'temperature': 23.5,
            'humidity': 65.2,
            'pressure': 1013.25
        }
        
        result = cassandra_service.write_telemetry(
            device_id=device_id,
            data=data
        )
        
        assert result is True
    
    def test_write_with_metadata(self, cassandra_service):
        """Test writing telemetry with metadata"""
        device_id = 1
        data = {'temperature': 23.5}
        metadata = {'location': 'room1', 'sensor': 'DHT22'}
        
        result = cassandra_service.write_telemetry(
            device_id=device_id,
            data=data,
            metadata=metadata
        )
        
        assert result is True
    
    def test_write_with_user_id(self, cassandra_service):
        """Test writing telemetry with user_id for user_data table"""
        device_id = 1
        user_id = 100
        data = {'temperature': 23.5}
        
        result = cassandra_service.write_telemetry_with_user(
            device_id=device_id,
            user_id=user_id,
            data=data
        )
        
        assert result is True
    
    def test_write_invalid_data_type(self, cassandra_service):
        """Test that non-numeric values are skipped"""
        device_id = 1
        data = {
            'temperature': 23.5,
            'status': 'active',  # Should be skipped
            'enabled': True      # Should be skipped
        }
        
        result = cassandra_service.write_telemetry(
            device_id=device_id,
            data=data
        )
        
        # Should succeed but only write numeric value
        assert result is True
    
    def test_write_with_custom_timestamp(self, cassandra_service):
        """Test writing data with custom timestamp"""
        device_id = 1
        data = {'temperature': 23.5}
        custom_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        result = cassandra_service.write_telemetry(
            device_id=device_id,
            data=data,
            timestamp=custom_time
        )
        
        assert result is True


class TestTelemetryRead:
    """Test reading telemetry data from Cassandra"""
    
    def test_get_device_telemetry(self, cassandra_service):
        """Test retrieving telemetry data for a device"""
        device_id = 1
        
        # Write some test data first
        cassandra_service.write_telemetry(
            device_id=device_id,
            data={'temperature': 23.5, 'humidity': 65.0}
        )
        
        # Read it back
        result = cassandra_service.get_device_telemetry(
            device_id=device_id,
            start_time='-1h'
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_get_telemetry_with_time_range(self, cassandra_service):
        """Test retrieving telemetry within a time range"""
        device_id = 1
        
        # Write data
        cassandra_service.write_telemetry(
            device_id=device_id,
            data={'temperature': 23.5}
        )
        
        # Query with time range
        result = cassandra_service.get_device_telemetry(
            device_id=device_id,
            start_time='-1h',
            end_time='now'
        )
        
        assert isinstance(result, list)
    
    def test_get_telemetry_with_limit(self, cassandra_service):
        """Test retrieving telemetry with limit"""
        device_id = 1
        
        # Write multiple data points
        for i in range(10):
            cassandra_service.write_telemetry(
                device_id=device_id,
                data={'temperature': 20.0 + i}
            )
        
        # Query with limit
        result = cassandra_service.get_device_telemetry(
            device_id=device_id,
            start_time='-1h',
            limit=5
        )
        
        assert len(result) <= 5
    
    def test_get_latest_telemetry(self, cassandra_service):
        """Test retrieving latest telemetry values"""
        device_id = 1
        
        # Write data
        cassandra_service.write_telemetry(
            device_id=device_id,
            data={'temperature': 25.0, 'humidity': 70.0}
        )
        
        # Get latest
        result = cassandra_service.get_latest_telemetry(device_id=device_id)
        
        assert result is not None
        assert 'temperature' in result
        assert 'humidity' in result
    
    def test_get_telemetry_nonexistent_device(self, cassandra_service):
        """Test querying telemetry for non-existent device"""
        result = cassandra_service.get_device_telemetry(
            device_id=99999,
            start_time='-1h'
        )
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestAggregatedData:
    """Test aggregated telemetry data operations"""
    
    def test_write_aggregated_data(self, cassandra_service):
        """Test writing aggregated data"""
        device_id = 1
        measurement = 'temperature'
        
        result = cassandra_service.write_aggregated_data(
            device_id=device_id,
            measurement_name=measurement,
            time_bucket=datetime.now(timezone.utc),
            aggregation_type='hourly',
            value=23.5,
            count=60,
            min_value=20.0,
            max_value=27.0
        )
        
        assert result is True
    
    def test_get_aggregated_data(self, cassandra_service):
        """Test retrieving aggregated data"""
        device_id = 1
        measurement = 'temperature'
        
        # Write aggregated data
        cassandra_service.write_aggregated_data(
            device_id=device_id,
            measurement_name=measurement,
            time_bucket=datetime.now(timezone.utc),
            aggregation_type='hourly',
            value=23.5,
            count=60
        )
        
        # Retrieve it
        result = cassandra_service.get_aggregated_data(
            device_id=device_id,
            measurement_name=measurement,
            aggregation_type='hourly',
            start_time='-24h'
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_compute_aggregation_mean(self, cassandra_service):
        """Test computing mean aggregation"""
        device_id = 1
        
        # Write multiple data points
        for i in range(10):
            cassandra_service.write_telemetry(
                device_id=device_id,
                data={'temperature': 20.0 + i}
            )
        
        # Compute aggregation
        result = cassandra_service.compute_aggregation(
            device_id=device_id,
            measurement_name='temperature',
            aggregation='mean',
            window='1h',
            start_time='-1h'
        )
        
        assert isinstance(result, list)


class TestUserTelemetry:
    """Test user-centric telemetry queries"""
    
    def test_get_user_telemetry(self, cassandra_service):
        """Test retrieving telemetry for all user's devices"""
        user_id = 100
        device_id = 1
        
        # Write data with user_id
        cassandra_service.write_telemetry_with_user(
            device_id=device_id,
            user_id=user_id,
            data={'temperature': 23.5}
        )
        
        # Query by user
        result = cassandra_service.get_user_telemetry(
            user_id=user_id,
            start_time='-1h'
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    def test_get_user_telemetry_count(self, cassandra_service):
        """Test counting telemetry records for a user"""
        user_id = 100
        device_id = 1
        
        # Write data
        cassandra_service.write_telemetry_with_user(
            device_id=device_id,
            user_id=user_id,
            data={'temperature': 23.5}
        )
        
        # Get count
        count = cassandra_service.get_user_telemetry_count(
            user_id=user_id,
            start_time='-1h'
        )
        
        assert count >= 0


class TestDataDeletion:
    """Test deleting telemetry data"""
    
    def test_delete_device_data(self, cassandra_service):
        """Test deleting telemetry data for a device"""
        device_id = 1
        
        # Write data
        cassandra_service.write_telemetry(
            device_id=device_id,
            data={'temperature': 23.5}
        )
        
        # Delete it
        result = cassandra_service.delete_device_data(
            device_id=device_id,
            start_time='-1h',
            end_time='now'
        )
        
        assert result is True
    
    def test_delete_old_data(self, cassandra_service):
        """Test deleting old data based on TTL"""
        device_id = 1
        old_time = datetime.now(timezone.utc) - timedelta(days=100)
        
        # Write old data
        cassandra_service.write_telemetry(
            device_id=device_id,
            data={'temperature': 23.5},
            timestamp=old_time
        )
        
        # Delete old data
        result = cassandra_service.delete_old_data(days=90)
        
        assert result is True


class TestDeviceMeasurements:
    """Test device measurement catalog"""
    
    def test_update_measurement_catalog(self, cassandra_service):
        """Test updating device measurement catalog"""
        device_id = 1
        measurement = 'temperature'
        
        result = cassandra_service.update_measurement_catalog(
            device_id=device_id,
            measurement_name=measurement,
            data_type='numeric',
            unit='celsius'
        )
        
        assert result is True
    
    def test_get_device_measurements(self, cassandra_service):
        """Test retrieving device measurement catalog"""
        device_id = 1
        
        # Update catalog
        cassandra_service.update_measurement_catalog(
            device_id=device_id,
            measurement_name='temperature',
            data_type='numeric',
            unit='celsius'
        )
        
        # Get catalog
        result = cassandra_service.get_device_measurements(device_id=device_id)
        
        assert isinstance(result, list)
        assert len(result) > 0


class TestTimeRangeParsing:
    """Test time range parsing utilities"""
    
    def test_parse_relative_time_hours(self, cassandra_service):
        """Test parsing relative time in hours"""
        result = cassandra_service._parse_time_range('-1h')
        assert isinstance(result, datetime)
    
    def test_parse_relative_time_days(self, cassandra_service):
        """Test parsing relative time in days"""
        result = cassandra_service._parse_time_range('-7d')
        assert isinstance(result, datetime)
    
    def test_parse_iso_format(self, cassandra_service):
        """Test parsing ISO format timestamp"""
        iso_time = datetime.now(timezone.utc).isoformat()
        result = cassandra_service._parse_time_range(iso_time)
        assert isinstance(result, datetime)
    
    def test_parse_now(self, cassandra_service):
        """Test parsing 'now' keyword"""
        result = cassandra_service._parse_time_range('now')
        assert isinstance(result, datetime)


class TestBatchOperations:
    """Test batch write operations"""
    
    def test_batch_write_telemetry(self, cassandra_service):
        """Test writing multiple telemetry records in batch"""
        records = [
            {'device_id': 1, 'data': {'temperature': 23.5}},
            {'device_id': 2, 'data': {'temperature': 24.0}},
            {'device_id': 3, 'data': {'temperature': 22.5}}
        ]
        
        result = cassandra_service.batch_write_telemetry(records)
        
        assert result is True
    
    def test_batch_write_with_timestamps(self, cassandra_service):
        """Test batch write with custom timestamps"""
        now = datetime.now(timezone.utc)
        records = [
            {
                'device_id': 1,
                'data': {'temperature': 23.5},
                'timestamp': now - timedelta(minutes=5)
            },
            {
                'device_id': 1,
                'data': {'temperature': 24.0},
                'timestamp': now
            }
        ]
        
        result = cassandra_service.batch_write_telemetry(records)
        
        assert result is True


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_write_with_invalid_device_id(self, cassandra_service):
        """Test writing with invalid device_id"""
        result = cassandra_service.write_telemetry(
            device_id=None,
            data={'temperature': 23.5}
        )
        
        assert result is False
    
    def test_write_with_empty_data(self, cassandra_service):
        """Test writing with empty data"""
        result = cassandra_service.write_telemetry(
            device_id=1,
            data={}
        )
        
        assert result is False
    
    def test_connection_failure_handling(self, cassandra_service):
        """Test handling of connection failures"""
        # This test would require mocking or stopping Cassandra
        # For now, just verify the method exists
        assert hasattr(cassandra_service, 'handle_connection_error')
    
    def test_query_timeout_handling(self, cassandra_service):
        """Test handling of query timeouts"""
        # Verify timeout configuration exists
        assert cassandra_service.query_timeout > 0


class TestPerformance:
    """Test performance characteristics"""
    
    def test_bulk_write_performance(self, cassandra_service):
        """Test writing large batch of data"""
        import time
        
        device_id = 1
        start_time = time.time()
        
        # Write 1000 records
        for i in range(1000):
            cassandra_service.write_telemetry(
                device_id=device_id,
                data={'temperature': 20.0 + (i % 10)}
            )
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 10 seconds)
        assert elapsed < 10.0
    
    def test_query_performance(self, cassandra_service):
        """Test query performance"""
        import time
        
        device_id = 1
        
        # Write some data
        for i in range(100):
            cassandra_service.write_telemetry(
                device_id=device_id,
                data={'temperature': 20.0 + i}
            )
        
        # Query it
        start_time = time.time()
        result = cassandra_service.get_device_telemetry(
            device_id=device_id,
            start_time='-1h',
            limit=100
        )
        elapsed = time.time() - start_time
        
        # Should be fast (< 1 second)
        assert elapsed < 1.0
        assert len(result) > 0
