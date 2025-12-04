"""
Test Device Groups Routes with NoSQL Integration (MongoDB for event logging)
Following TDD approach
"""

import pytest
from unittest.mock import Mock, patch
from src.models import DeviceGroup, Device, User


class TestGroupCreationWithNoSQL:
    """Test group creation with MongoDB logging"""
    
    def test_create_group_logs_to_mongodb(self, client, test_user):
        """Test that group creation logs event to MongoDB"""
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                '/api/v1/groups',
                headers={'X-User-ID': test_user.user_id},
                json={
                    'name': 'Living Room',
                    'description': 'All living room devices',
                    'color': '#FF5733'
                }
            )
            
            assert response.status_code == 201
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.created'
            assert event_data['details']['group_name'] == 'Living Room'


class TestGroupUpdateWithNoSQL:
    """Test group update with MongoDB logging"""
    
    def test_update_group_logs_to_mongodb(self, client, test_user, test_group):
        """Test that group update logs event to MongoDB"""
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.put(
                f'/api/v1/groups/{test_group.id}',
                headers={'X-User-ID': test_user.user_id},
                json={
                    'name': 'Updated Living Room',
                    'color': '#00FF00'
                }
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.updated'


class TestGroupDeletionWithNoSQL:
    """Test group deletion with MongoDB logging"""
    
    def test_delete_group_logs_to_mongodb(self, client, test_user, test_group):
        """Test that group deletion logs event to MongoDB"""
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.delete(
                f'/api/v1/groups/{test_group.id}',
                headers={'X-User-ID': test_user.user_id}
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.deleted'


class TestDeviceGroupMembershipWithNoSQL:
    """Test device-group membership with MongoDB logging"""
    
    def test_add_device_to_group_logs_to_mongodb(self, client, test_user, test_group, test_device):
        """Test that adding device to group logs event to MongoDB"""
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                f'/api/v1/groups/{test_group.id}/devices',
                headers={'X-User-ID': test_user.user_id},
                json={'device_id': test_device.id}
            )
            
            assert response.status_code == 201
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.device_added'
            assert event_data['details']['device_id'] == test_device.id
            assert event_data['details']['group_id'] == test_group.id
    
    def test_remove_device_from_group_logs_to_mongodb(self, client, test_user, test_group, test_device):
        """Test that removing device from group logs event to MongoDB"""
        # First add device to group
        from src.models import DeviceGroupMember, db
        membership = DeviceGroupMember(group_id=test_group.id, device_id=test_device.id)
        db.session.add(membership)
        db.session.commit()
        
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.delete(
                f'/api/v1/groups/{test_group.id}/devices/{test_device.id}',
                headers={'X-User-ID': test_user.user_id}
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.device_removed'
    
    def test_bulk_add_devices_logs_to_mongodb(self, client, test_user, test_group):
        """Test that bulk adding devices logs event to MongoDB"""
        # Create multiple devices
        from src.models import Device, db
        devices = []
        for i in range(3):
            device = Device(
                name=f'Device {i}',
                device_type='sensor',
                user_id=test_user.id
            )
            db.session.add(device)
            devices.append(device)
        db.session.commit()
        
        device_ids = [d.id for d in devices]
        
        with patch('src.routes.groups.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                f'/api/v1/groups/{test_group.id}/devices/bulk',
                headers={'X-User-ID': test_user.user_id},
                json={'device_ids': device_ids}
            )
            
            assert response.status_code == 201
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'group.devices_bulk_added'
            assert event_data['details']['count'] == 3


# Fixtures
@pytest.fixture
def test_user(app):
    """Create a test user"""
    from src.models import User, db
    
    user = User(
        username='testuser',
        email='test@example.com'
    )
    user.set_password('password123')
    
    db.session.add(user)
    db.session.commit()
    
    yield user
    
    db.session.delete(user)
    db.session.commit()


@pytest.fixture
def test_device(app, test_user):
    """Create a test device"""
    from src.models import Device, db
    
    device = Device(
        name='Test Device',
        device_type='sensor',
        user_id=test_user.id
    )
    
    db.session.add(device)
    db.session.commit()
    
    yield device
    
    db.session.delete(device)
    db.session.commit()


@pytest.fixture
def test_group(app, test_user):
    """Create a test group"""
    from src.models import DeviceGroup, db
    
    group = DeviceGroup(
        name='Test Group',
        description='Test group description',
        user_id=test_user.id,
        color='#FF5733'
    )
    
    db.session.add(group)
    db.session.commit()
    
    yield group
    
    db.session.delete(group)
    db.session.commit()
