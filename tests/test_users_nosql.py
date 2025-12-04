"""
Test User Routes with NoSQL Integration (MongoDB for audit logging)
Following TDD approach
"""

import pytest
from unittest.mock import Mock, patch
from src.models import User


class TestUserCreationWithNoSQL:
    """Test user creation with MongoDB audit logging"""
    
    def test_register_user_logs_to_mongodb(self, client):
        """Test that user registration logs event to MongoDB"""
        with patch('src.routes.auth.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                '/api/v1/auth/register',
                json={
                    'username': 'newuser',
                    'email': 'newuser@example.com',
                    'password': 'password123'
                }
            )
            
            assert response.status_code == 201
            
            # Verify MongoDB logging was called
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'user.registered'
            assert event_data['details']['username'] == 'newuser'


class TestUserLoginWithNoSQL:
    """Test user login with MongoDB audit logging"""
    
    def test_login_logs_to_mongodb(self, client, test_user):
        """Test that user login logs event to MongoDB"""
        with patch('src.routes.auth.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.post(
                '/api/v1/auth/login',
                json={
                    'username': test_user.username,
                    'password': 'password123'
                }
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'user.login'
            assert event_data['details']['username'] == test_user.username


class TestUserUpdateWithNoSQL:
    """Test user update with MongoDB audit logging"""
    
    def test_update_user_logs_to_mongodb(self, client, test_user):
        """Test that user update logs event to MongoDB"""
        with patch('src.routes.users.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.put(
                f'/api/v1/users/{test_user.user_id}',
                headers={'X-User-ID': test_user.user_id},
                json={
                    'email': 'newemail@example.com'
                }
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'user.updated'
            assert 'email' in event_data['details']['updated_fields']


class TestUserDeactivationWithNoSQL:
    """Test user deactivation with MongoDB audit logging"""
    
    def test_deactivate_user_logs_to_mongodb(self, client, test_user, admin_token):
        """Test that user deactivation logs event to MongoDB"""
        with patch('src.routes.users.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.patch(
                f'/api/v1/users/{test_user.user_id}/deactivate',
                headers={'Authorization': f'admin {admin_token}'}
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'user.deactivated'


class TestUserDeletionWithNoSQL:
    """Test user deletion with MongoDB audit logging"""
    
    def test_delete_user_logs_to_mongodb(self, client, admin_token):
        """Test that user deletion logs event to MongoDB"""
        # Create a user to delete
        from src.models import User, db
        user = User(username='todelete', email='delete@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        user_id = user.user_id
        
        with patch('src.routes.users.mongodb_service') as mock_mongo:
            mock_mongo.log_event = Mock()
            
            response = client.delete(
                f'/api/v1/users/{user_id}',
                headers={'Authorization': f'admin {admin_token}'}
            )
            
            assert response.status_code == 200
            
            # Verify MongoDB logging
            assert mock_mongo.log_event.called
            event_data = mock_mongo.log_event.call_args[0][0]
            assert event_data['event_type'] == 'user.deleted'


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
def admin_token():
    """Return admin token"""
    import os
    return os.environ.get('IOTFLOW_ADMIN_TOKEN', 'test')
