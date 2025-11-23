"""
TDD Test Suite for Admin-Only User Deletion
Following TDD approach - write tests first, then implement functionality
"""

import os
import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app
from src.models import db, User


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
def regular_user(app):
    """Create regular (non-admin) user"""
    with app.app_context():
        user = User(
            username='regularuser',
            email='regular@example.com',
            password_hash='hash'
        )
        user.is_admin = False
        db.session.add(user)
        db.session.commit()
        return {
            'id': user.id,
            'user_id': user.user_id,
            'username': user.username,
            'is_admin': user.is_admin
        }


@pytest.fixture
def admin_user(app):
    """Create admin user"""
    with app.app_context():
        user = User(
            username='adminuser',
            email='admin@example.com',
            password_hash='hash'
        )
        user.is_admin = True
        db.session.add(user)
        db.session.commit()
        return {
            'id': user.id,
            'user_id': user.user_id,
            'username': user.username,
            'is_admin': user.is_admin
        }


@pytest.fixture
def target_user(app):
    """Create target user to be deleted"""
    with app.app_context():
        user = User(
            username='targetuser',
            email='target@example.com',
            password_hash='hash'
        )
        db.session.add(user)
        db.session.commit()
        return {
            'id': user.id,
            'user_id': user.user_id,
            'username': user.username
        }


def get_admin_token():
    """Get admin token for testing"""
    return os.environ.get('IOTFLOW_ADMIN_TOKEN', 'test')


class TestAdminOnlyUserDeletion:
    """Test that only admins can delete users"""
    
    def test_delete_user_without_token(self, client, target_user):
        """Test deleting user without authentication token fails"""
        response = client.delete(f'/api/v1/users/{target_user["user_id"]}')
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data or 'message' in data
    
    def test_delete_user_with_invalid_token(self, client, target_user):
        """Test deleting user with invalid admin token fails"""
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': 'admin invalid-token'}
        )
        
        assert response.status_code == 403
    
    def test_delete_user_as_regular_user_fails(self, app, client, regular_user, target_user):
        """Test that users without admin token cannot delete other users"""
        # Try without admin token (just wrong format)
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': 'Bearer some-token'}
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_delete_user_as_admin_succeeds(self, app, client, admin_user, target_user):
        """Test that users with admin token can delete other users"""
        admin_token = get_admin_token()
        
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_deleted_user_is_removed(self, app, client, admin_user, target_user):
        """Test that deleted user is permanently removed (hard delete)"""
        admin_token = get_admin_token()
        
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        
        # Verify user is permanently deleted
        with app.app_context():
            user = User.query.filter_by(user_id=target_user['user_id']).first()
            assert user is None  # User no longer exists in database
    
    def test_delete_nonexistent_user(self, app, client, admin_user):
        """Test deleting non-existent user returns 404"""
        admin_token = get_admin_token()
        
        response = client.delete(
            '/api/v1/users/nonexistent-user-id',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_regular_user_cannot_delete_self(self, app, client, regular_user):
        """Test that users without admin token cannot delete themselves"""
        response = client.delete(
            f'/api/v1/users/{regular_user["user_id"]}'
        )
        
        assert response.status_code == 401
    
    def test_admin_cannot_delete_admin(self, app, client, admin_user):
        """Test that admin users cannot be deleted (protection)"""
        admin_token = get_admin_token()
        
        response = client.delete(
            f'/api/v1/users/{admin_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'admin' in data['error'].lower()
    
    def test_delete_user_response_structure(self, app, client, admin_user, target_user):
        """Test the response structure of successful deletion"""
        admin_token = get_admin_token()
        
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert 'message' in data
        assert data['status'] == 'success'


class TestAdminTokenValidation:
    """Test admin token validation"""
    
    def test_token_with_admin_false(self, app, client, regular_user, target_user):
        """Test wrong token format is rejected"""
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': 'Bearer some-token'}
        )
        
        assert response.status_code == 401
    
    def test_token_with_admin_true(self, app, client, admin_user, target_user):
        """Test valid admin token is accepted"""
        admin_token = get_admin_token()
        
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 200
    
    def test_expired_admin_token(self, app, client, admin_user, target_user):
        """Test invalid admin token is rejected"""
        response = client.delete(
            f'/api/v1/users/{target_user["user_id"]}',
            headers={'Authorization': 'admin wrong_token'}
        )
        
        assert response.status_code == 403

    def test_cannot_delete_admin_user(self, app, client, admin_user):
        """Test that admin users cannot be deleted"""
        admin_token = os.environ.get('IOTFLOW_ADMIN_TOKEN', 'test_admin_token')
        
        response = client.delete(
            f'/api/v1/users/{admin_user["user_id"]}',
            headers={'Authorization': f'admin {admin_token}'}
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'admin' in data['error'].lower()
        
        # Verify admin user still exists
        with app.app_context():
            user = User.query.filter_by(user_id=admin_user['user_id']).first()
            assert user is not None
            assert user.is_admin is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
