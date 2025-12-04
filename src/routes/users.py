"""
User management routes
"""

from flask import Blueprint, request, jsonify, current_app
from src.models import User, db
from src.middleware.auth import require_admin_token
from src.middleware.security import security_headers_middleware
from datetime import datetime, timezone

# Import NoSQL services
from src.services.redis_cache import RedisCacheService
from src.services.mongodb_service import MongoDBService

# Create blueprint for user routes
user_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")

# Initialize NoSQL services
redis_service = RedisCacheService()
mongodb_service = MongoDBService()


@user_bp.route("/<user_id>", methods=["GET"])
@security_headers_middleware()
def get_user(user_id):
    """Get user by ID
    ---
    tags:
      - Users
    summary: Get user details
    description: Get details of a specific user by ID (requires User ID header to match or admin token)
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
        description: User UUID
      - name: X-User-ID
        in: header
        schema:
          type: string
        description: Requesting user's UUID (must match user_id or use admin token)
    responses:
      200:
        description: User details
      401:
        description: Unauthorized
      403:
        description: Forbidden - can only view own profile
      404:
        description: User not found
    """
    try:
        # Check authentication - either admin token or matching user ID
        auth_header = request.headers.get("Authorization", "")
        requesting_user_id = request.headers.get("X-User-ID")
        
        # Check if admin
        is_admin = False
        if auth_header.startswith("admin "):
            import os
            ADMIN_TOKEN = os.environ.get("IOTFLOW_ADMIN_TOKEN", "test")
            token = auth_header.split(" ", 1)[1] if len(auth_header.split(" ", 1)) > 1 else ""
            is_admin = (token == ADMIN_TOKEN)
        
        # If not admin, must provide matching user ID
        if not is_admin:
            if not requesting_user_id:
                return jsonify({
                    "error": "Authentication required",
                    "message": "X-User-ID header required"
                }), 401
            
            if requesting_user_id != user_id:
                return jsonify({
                    "error": "Forbidden",
                    "message": "You can only view your own profile"
                }), 403
        
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        return jsonify({
            "status": "success",
            "user": user.to_dict()
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting user: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve user",
            "message": "An error occurred while retrieving the user"
        }), 500


@user_bp.route("", methods=["GET"])
@security_headers_middleware()
@require_admin_token
def list_users():
    """List all users (Admin only)
    ---
    tags:
      - Users
    summary: List users (Admin only)
    description: Get list of all users with pagination. Requires admin privileges.
    security:
      - BearerAuth: []
    parameters:
      - name: limit
        in: query
        schema:
          type: integer
          default: 100
      - name: offset
        in: query
        schema:
          type: integer
          default: 0
    responses:
      200:
        description: List of users
      401:
        description: Unauthorized - invalid or missing token
      403:
        description: Forbidden - admin privileges required
    """
    try:
        # Get pagination parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get users
        users = User.query.limit(limit).offset(offset).all()
        
        return jsonify({
            "status": "success",
            "users": [user.to_dict() for user in users],
            "meta": {
                "total": User.query.count(),
                "limit": limit,
                "offset": offset
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            "error": "Failed to list users",
            "message": "An error occurred while listing users"
        }), 500


@user_bp.route("/<user_id>", methods=["PUT"])
@security_headers_middleware()
def update_user(user_id):
    """Update user information
    ---
    tags:
      - Users
    summary: Update user
    description: Update user information (requires User ID header to match or admin token)
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
      - name: X-User-ID
        in: header
        schema:
          type: string
        description: Requesting user's UUID (must match user_id or use admin token)
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              username:
                type: string
              email:
                type: string
              password:
                type: string
              is_active:
                type: boolean
    responses:
      200:
        description: User updated
      401:
        description: Unauthorized
      403:
        description: Forbidden - can only update own profile
      404:
        description: User not found
    """
    try:
        # Check authentication - either admin token or matching user ID
        auth_header = request.headers.get("Authorization", "")
        requesting_user_id = request.headers.get("X-User-ID")
        
        # Check if admin
        is_admin = False
        if auth_header.startswith("admin "):
            import os
            ADMIN_TOKEN = os.environ.get("IOTFLOW_ADMIN_TOKEN", "test")
            token = auth_header.split(" ", 1)[1] if len(auth_header.split(" ", 1)) > 1 else ""
            is_admin = (token == ADMIN_TOKEN)
        
        # If not admin, must provide matching user ID
        if not is_admin:
            if not requesting_user_id:
                return jsonify({
                    "error": "Authentication required",
                    "message": "X-User-ID header required"
                }), 401
            
            if requesting_user_id != user_id:
                return jsonify({
                    "error": "Forbidden",
                    "message": "You can only update your own profile"
                }), 403
        
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update allowed fields
        if 'email' in data:
            # Check if email is already taken by another user
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.user_id != user_id:
                return jsonify({
                    "error": "Email already exists",
                    "message": f"Email '{data['email']}' is already in use"
                }), 409
            user.email = data['email']
        
        if 'username' in data:
            # Check if username is already taken by another user
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.user_id != user_id:
                return jsonify({
                    "error": "Username already exists",
                    "message": f"Username '{data['username']}' is already in use"
                }), 409
            user.username = data['username']
        
        if 'password' in data:
            user.set_password(data['password'])
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        current_app.logger.info(f"User updated: {user.username} (ID: {user.user_id})")
        
        # Log event to MongoDB
        try:
            mongodb_service.log_event({
                'event_type': 'user.updated',
                'user_id': user.id,
                'timestamp': datetime.now(timezone.utc),
                'details': {
                    'updated_fields': list(data.keys()),
                    'username': user.username
                }
            })
        except Exception as e:
            current_app.logger.warning(f"Failed to log event to MongoDB: {e}")
        
        return jsonify({
            "status": "success",
            "message": "User updated successfully",
            "user": user.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({
            "error": "User update failed",
            "message": "An error occurred while updating the user"
        }), 500


@user_bp.route("/<user_id>", methods=["DELETE"])
@security_headers_middleware()
@require_admin_token
def delete_user(user_id):
    """Delete a user permanently (Admin only)
    ---
    tags:
      - Users
    summary: Delete user (Admin only)
    description: Permanently delete a user account and all associated data. Requires admin privileges.
    security:
      - BearerAuth: []
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: User deleted successfully
      401:
        description: Unauthorized - invalid or missing token
      403:
        description: Forbidden - admin privileges required
      404:
        description: User not found
    """
    try:
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        # Prevent deletion of admin users
        if user.is_admin:
            return jsonify({
                "error": "Cannot delete admin",
                "message": "Admin users cannot be deleted"
            }), 403
        
        username = user.username
        
        # Hard delete - permanently remove from database
        # Note: Associated devices will be deleted due to CASCADE foreign key
        db.session.delete(user)
        db.session.commit()
        
        current_app.logger.info(f"User permanently deleted: {username} (ID: {user_id})")
        
        return jsonify({
            "status": "success",
            "message": f"User '{username}' deleted permanently"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({
            "error": "User deletion failed",
            "message": "An error occurred while deleting the user"
        }), 500


@user_bp.route("/<user_id>/deactivate", methods=["PATCH"])
@security_headers_middleware()
@require_admin_token
def deactivate_user(user_id):
    """Deactivate a user account (soft delete) (Admin only)
    ---
    tags:
      - Users
    summary: Deactivate user (Admin only)
    description: Deactivate a user account without deleting data. User will not be able to log in. Requires admin privileges.
    security:
      - BearerAuth: []
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: User deactivated successfully
      401:
        description: Unauthorized - invalid or missing token
      403:
        description: Forbidden - admin privileges required
      404:
        description: User not found
    """
    try:
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        # Prevent deactivation of admin users
        if user.is_admin:
            return jsonify({
                "error": "Cannot deactivate admin",
                "message": "Admin users cannot be deactivated"
            }), 403
        
        # Check if already deactivated
        if not user.is_active:
            return jsonify({
                "status": "success",
                "message": f"User '{user.username}' is already deactivated"
            }), 200
        
        # Soft delete - deactivate instead of deleting
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        current_app.logger.info(f"User deactivated: {user.username} (ID: {user.user_id})")
        
        return jsonify({
            "status": "success",
            "message": f"User '{user.username}' deactivated successfully"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deactivating user: {str(e)}")
        return jsonify({
            "error": "User deactivation failed",
            "message": "An error occurred while deactivating the user"
        }), 500


@user_bp.route("/<user_id>/activate", methods=["PATCH"])
@security_headers_middleware()
@require_admin_token
def activate_user(user_id):
    """Activate a deactivated user account (Admin only)
    ---
    tags:
      - Users
    summary: Activate user (Admin only)
    description: Reactivate a previously deactivated user account. Requires admin privileges.
    security:
      - BearerAuth: []
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: User activated successfully
      401:
        description: Unauthorized - invalid or missing token
      403:
        description: Forbidden - admin privileges required
      404:
        description: User not found
    """
    try:
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        # Check if already active
        if user.is_active:
            return jsonify({
                "status": "success",
                "message": f"User '{user.username}' is already active"
            }), 200
        
        # Activate user
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        current_app.logger.info(f"User activated: {user.username} (ID: {user.user_id})")
        
        return jsonify({
            "status": "success",
            "message": f"User '{user.username}' activated successfully"
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error activating user: {str(e)}")
        return jsonify({
            "error": "User activation failed",
            "message": "An error occurred while activating the user"
        }), 500
