"""
Tests for user deactivation/activation endpoints
"""

import os
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['IOTFLOW_ADMIN_TOKEN'] = 'test_admin_token'

from app import create_app
from src.models import db, User


def get_admin_token():
    """Get admin token for testing"""
    return os.environ.get('IOTFLOW_ADMIN_TOKEN', 'test_admin_token')


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['IOTFLOW_ADMIN_TOKEN'] = 'test_admin_token'
    
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
    """Create test user"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        return {
            'id': user.id,
            'user_id': user.user_id,
            'username': user.username
        }


class TestUserDeactivation:
    """Test user deactivation endpoint"""
    
    def test_deactivate_user_requires_admin(self, client, test_user):
        """Test that deactivation requires admin token"""
        response = client.patch(f'/api/v1/users/{test_user["user_id"]}/deactivate')
        
        assert response.status_code == 401
    
    def test_deactivate_user_with_invalid_token(self, client, test_user):
        """Test deactivation with invalid admin token"""
        response = client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': 'admin invalid_token'}
        )
        
        assert response.status_code == 403
    
    def test_deactivate_user_success(self, app, client, test_user):
        """Test successful user deactivation"""
        admin_token = get_admin_token()
        
        response = client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'deactivated' in data['message'].lower()
        
        # Verify user is deactivated in database
        with app.app_context():
            user = User.query.filter_by(user_id=test_user['user_id']).first()
            assert user is not None
            assert user.is_active is False
    
    def test_deactivate_already_deactivated_user(self, app, client, test_user):
        """Test deactivating an already deactivated user"""
        admin_token = get_admin_token()
        
        # Deactivate first time
        client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        # Deactivate second time
        response = client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'already deactivated' in data['message'].lower()
    
    def test_deactivate_nonexistent_user(self, client):
        """Test deactivating non-existent user"""
        admin_token = get_admin_token()
        
        response = client.patch(
            '/api/v1/users/nonexistent-user-id/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 404


class TestUserActivation:
    """Test user activation endpoint"""
    
    def test_activate_user_requires_admin(self, client, test_user):
        """Test that activation requires admin token"""
        response = client.patch(f'/api/v1/users/{test_user["user_id"]}/activate')
        
        assert response.status_code == 401
    
    def test_activate_deactivated_user(self, app, client, test_user):
        """Test activating a deactivated user"""
        admin_token = get_admin_token()
        
        # First deactivate the user
        client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        # Now activate the user
        response = client.patch(
            f'/api/v1/users/{test_user["user_id"]}/activate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'activated' in data['message'].lower()
        
        # Verify user is active in database
        with app.app_context():
            user = User.query.filter_by(user_id=test_user['user_id']).first()
            assert user is not None
            assert user.is_active is True
    
    def test_activate_already_active_user(self, client, test_user):
        """Test activating an already active user"""
        admin_token = get_admin_token()
        
        response = client.patch(
            f'/api/v1/users/{test_user["user_id"]}/activate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'already active' in data['message'].lower()
    
    def test_activate_nonexistent_user(self, client):
        """Test activating non-existent user"""
        admin_token = get_admin_token()
        
        response = client.patch(
            '/api/v1/users/nonexistent-user-id/activate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 404


class TestDeactivationVsDeletion:
    """Test the difference between deactivation and deletion"""
    
    def test_deactivated_user_still_exists(self, app, client, test_user):
        """Test that deactivated user still exists in database"""
        admin_token = get_admin_token()
        
        # Deactivate user
        client.patch(
            f'/api/v1/users/{test_user["user_id"]}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        # User should still be retrievable
        response = client.get(
            f'/api/v1/users/{test_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['is_active'] is False
    
    def test_deleted_user_does_not_exist(self, app, client, test_user):
        """Test that deleted user is removed from database"""
        admin_token = get_admin_token()
        
        # Delete user
        client.delete(
            f'/api/v1/users/{test_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        # User should not be retrievable
        response = client.get(
            f'/api/v1/users/{test_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 404

    def test_cannot_deactivate_admin_user(self, app, client):
        """Test that admin users cannot be deactivated"""
        admin_token = get_admin_token()
        
        # Create an admin user
        with app.app_context():
            admin_user = User(
                username='adminuser',
                email='admin@example.com',
                password_hash='hash'
            )
            admin_user.is_admin = True
            db.session.add(admin_user)
            db.session.commit()
            admin_user_id = admin_user.user_id
        
        # Try to deactivate the admin user
        response = client.patch(
            f'/api/v1/users/{admin_user_id}/deactivate',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'admin' in data['error'].lower()
        
        # Verify admin user is still active
        with app.app_context():
            user = User.query.filter_by(user_id=admin_user_id).first()
            assert user is not None
            assert user.is_active is True
            assert user.is_admin is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
