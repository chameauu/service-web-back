from flask import Blueprint, request, jsonify, current_app
from src.models import Device, User, db
from src.middleware.auth import (
    authenticate_device,
    validate_json_payload,
    rate_limit_device,
)
from src.middleware.monitoring import (
    device_heartbeat_monitor,
    request_metrics_middleware,
)
from src.middleware.security import (
    security_headers_middleware,
    input_sanitization_middleware,
)
from datetime import datetime, timezone

# Import NoSQL services
from src.services.redis_cache import RedisCacheService
from src.services.mongodb_service import MongoDBService

# Create blueprint for device routes
device_bp = Blueprint("devices", __name__, url_prefix="/api/v1/devices")

# Initialize NoSQL services
redis_service = RedisCacheService()
mongodb_service = MongoDBService()


@device_bp.route("/register", methods=["POST"])
@security_headers_middleware()
@request_metrics_middleware()
@rate_limit_device(max_requests=10, window=300, per_device=False)  # 10 registrations per 5 minutes per IP
@validate_json_payload(["name", "device_type"])
@input_sanitization_middleware()
def register_device():
    """Register a new IoT device
    ---
    tags:
      - Devices
    summary: Register new device
    description: Register a new IoT device with user authentication via X-User-ID header
    parameters:
      - name: X-User-ID
        in: header
        required: true
        schema:
          type: string
        description: User ID for authentication
        example: fd596e05-a937-4eea-bbaf-2779686b9f1b
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
              - device_type
            properties:
              name:
                type: string
                example: Temperature Sensor 1
              device_type:
                type: string
                example: sensor
              description:
                type: string
                example: Temperature and humidity sensor
              location:
                type: string
                example: Living Room
              firmware_version:
                type: string
                example: 1.0.0
              hardware_version:
                type: string
                example: v2.1
    responses:
      201:
        description: Device registered successfully
      400:
        description: Invalid input
      401:
        description: Authentication failed
    """
    try:
        data = request.validated_json

        # Get user_id from header
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return (
                jsonify(
                    {
                        "error": "Authentication required",
                        "message": "X-User-ID header is required",
                    }
                ),
                401,
            )

        # Verify user exists and is active using user_id directly
        user = User.query.filter_by(user_id=user_id, is_active=True).first()
        if not user:
            return (
                jsonify(
                    {
                        "error": "Authentication failed",
                        "message": "Invalid user_id or user is not active",
                    }
                ),
                401,
            )

        # Check if device name already exists for this user
        existing_device = Device.query.filter_by(name=data["name"], user_id=user.id).first()
        if existing_device:
            return (
                jsonify(
                    {
                        "error": "Device name already exists",
                        "message": "Please choose a different device name",
                    }
                ),
                409,
            )

        # Create new device using the user's internal ID
        device = Device(
            name=data["name"],
            description=data.get("description", ""),
            device_type=data["device_type"],
            location=data.get("location", ""),
            firmware_version=data.get("firmware_version", ""),
            hardware_version=data.get("hardware_version", ""),
            user_id=user.id,  # Use the internal user ID from the query
        )

        db.session.add(device)
        db.session.commit()

        current_app.logger.info(f"New device registered: {device.name} (ID: {device.id}) by user_id: {user_id}")

        # Cache device info in Redis
        try:
            redis_service.cache_device_info(device.id, {
                'device_id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'status': device.status,
                'user_id': device.user_id
            }, ttl=3600)
            
            # Cache API key mapping
            redis_service.cache_api_key(device.api_key, {
                'device_id': device.id,
                'user_id': device.user_id,
                'status': device.status
            }, ttl=3600)
        except Exception as e:
            current_app.logger.warning(f"Failed to cache device in Redis: {e}")

        # Log event to MongoDB
        try:
            mongodb_service.log_event({
                'event_type': 'device.registered',
                'device_id': device.id,
                'user_id': device.user_id,
                'timestamp': datetime.now(timezone.utc),
                'details': {
                    'device_name': device.name,
                    'device_type': device.device_type,
                    'location': device.location
                }
            })
        except Exception as e:
            current_app.logger.warning(f"Failed to log event to MongoDB: {e}")

        response_data = device.to_dict()
        response_data["api_key"] = device.api_key  # Include API key in registration response
        response_data["owner"] = {"username": user.username, "email": user.email}

        return (
            jsonify({"message": "Device registered successfully", "device": response_data}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering device: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Registration failed",
                    "message": "An error occurred while registering the device",
                }
            ),
            500,
        )


@device_bp.route("/user/<user_id>", methods=["GET"])
@security_headers_middleware()
@request_metrics_middleware()
def get_user_devices(user_id):
    """Get all devices for a specific user
    ---
    tags:
      - Devices
    summary: Get user devices
    description: Get list of all devices belonging to a specific user (requires User ID header to match or admin token)
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
      - name: status
        in: query
        schema:
          type: string
          enum: [active, inactive, maintenance]
        description: Filter by device status
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
        description: List of user devices
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: success
                user_id:
                  type: string
                total_devices:
                  type: integer
                devices:
                  type: array
                  items:
                    type: object
      401:
        description: Unauthorized
      403:
        description: Forbidden - can only view own devices
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
                    "message": "You can only view your own devices"
                }), 403
        
        # Find user by user_id
        user = User.query.filter_by(user_id=user_id).first()
        
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404
        
        # Get query parameters
        status_filter = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = Device.query.filter_by(user_id=user.id)
        
        # Apply status filter if provided
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Get total count before pagination
        total_devices = query.count()
        
        # Apply pagination
        devices = query.limit(limit).offset(offset).all()
        
        # Format response
        device_list = []
        for device in devices:
            device_dict = device.to_dict()
            # Don't include API key in list response for security
            device_dict.pop('api_key', None)
            device_list.append(device_dict)
        
        current_app.logger.info(f"Retrieved {len(device_list)} devices for user: {user.username}")
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "username": user.username,
            "total_devices": total_devices,
            "devices": device_list,
            "meta": {
                "limit": limit,
                "offset": offset,
                "returned": len(device_list)
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error getting user devices: {str(e)}")
        return jsonify({
            "error": "Failed to retrieve devices",
            "message": "An error occurred while retrieving user devices"
        }), 500


@device_bp.route("/status", methods=["GET"])
@security_headers_middleware()
@request_metrics_middleware()
@authenticate_device
@device_heartbeat_monitor()
def get_device_status():
    """Get current device status"""
    try:
        device = request.device

        # Try to get cached device info from Redis
        cached_info = redis_service.get_device_info(device.id)
        
        # Telemetry count - could be added later if needed
        telemetry_count = 0

        response = device.to_dict()
        response["telemetry_count"] = telemetry_count

        # Check device online status from Redis first, then database
        is_online = redis_service.is_device_online(device.id)
        if not is_online and device.last_seen:
            # Fallback to database check
            now = datetime.now(timezone.utc)
            last_seen = device.last_seen
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            is_online = (now - last_seen).total_seconds() < 300  # 5 minutes

        response["is_online"] = is_online
        response["cached"] = cached_info is not None

        return jsonify({"status": "success", "device": response}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting device status: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Status retrieval failed",
                    "message": "An error occurred while retrieving device status",
                }
            ),
            500,
        )


# REMOVED: POST /api/v1/devices/telemetry - Duplicate of POST /api/v1/telemetry
# Use POST /api/v1/telemetry instead (more flexible, supports metadata and custom timestamps)


# REMOVED: GET /api/v1/devices/telemetry - Use GET /api/v1/telemetry/{device_id} instead


@device_bp.route("/config", methods=["PUT"])
@authenticate_device
@validate_json_payload(["status"])
def update_device_info():
    """Update device information (status, location, versions)"""
    try:
        device = request.device
        data = request.validated_json

        # Update allowed fields
        if "status" in data and data["status"] in ["active", "inactive", "maintenance"]:
            device.status = data["status"]

        if "location" in data:
            device.location = data["location"]

        if "firmware_version" in data:
            device.firmware_version = data["firmware_version"]

        if "hardware_version" in data:
            device.hardware_version = data["hardware_version"]

        device.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        current_app.logger.info(f"Device configuration updated: {device.name} (ID: {device.id})")

        # Update Redis cache
        try:
            redis_service.cache_device_info(device.id, {
                'device_id': device.id,
                'name': device.name,
                'device_type': device.device_type,
                'status': device.status,
                'user_id': device.user_id,
                'location': device.location
            }, ttl=3600)
        except Exception as e:
            current_app.logger.warning(f"Failed to update device cache: {e}")

        # Log event to MongoDB
        try:
            mongodb_service.log_event({
                'event_type': 'device.config_updated',
                'device_id': device.id,
                'user_id': device.user_id,
                'timestamp': datetime.now(timezone.utc),
                'details': {
                    'updated_fields': list(data.keys())
                }
            })
        except Exception as e:
            current_app.logger.warning(f"Failed to log event to MongoDB: {e}")

        return (
            jsonify(
                {
                    "message": "Device configuration updated successfully",
                    "device": device.to_dict(),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating device config: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Configuration update failed",
                    "message": "An error occurred while updating device configuration",
                }
            ),
            500,
        )


@device_bp.route("/credentials", methods=["GET"])
@security_headers_middleware()
@request_metrics_middleware()
@rate_limit_device(max_requests=10, window=60, per_device=False)  # 10 requests per minute per IP
def get_device_credentials():
    """Get device credentials using API key authentication"""
    try:
        # Get API key from headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return (
                jsonify(
                    {
                        "error": "API key required",
                        "message": "X-API-Key header is required",
                    }
                ),
                401,
            )

        # Find device by API key (allow inactive devices for credentials lookup)
        device = Device.query.filter_by(api_key=api_key).first()
        if not device:
            return (
                jsonify({"error": "Invalid API key", "message": "Device not found"}),
                404,
            )

        # Check if device is active
        # if device.status != 'active':
        #     return jsonify({
        #         'error': 'Device inactive',
        #         'message': f'Device status is {device.status}. Please contact administrator to activate device.',
        #         'device_status': device.status
        #     }), 403

        # Update device last_seen
        device.update_last_seen()

        # Get user information
        user = User.query.filter_by(id=device.user_id).first()

        # Return device credentials
        credentials = {
            "id": device.id,
            "name": device.name,
            "device_type": device.device_type,
            "user_id": str(device.user_id) if device.user_id else None,
            "status": device.status,
        }

        # Add user info if available
        if user:
            credentials["owner"] = {"username": user.username, "user_id": user.user_id}

        current_app.logger.info(f"Credentials retrieved for device {device.name} (ID: {device.id})")

        return jsonify({"status": "success", "device": credentials}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting device credentials: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Credentials retrieval failed",
                    "message": "An error occurred while retrieving device credentials",
                }
            ),
            500,
        )


@device_bp.route("/heartbeat", methods=["POST"])
@security_headers_middleware()
@request_metrics_middleware()
@authenticate_device
@device_heartbeat_monitor()
@rate_limit_device(max_requests=30, window=60)  # 30 heartbeats per minute
def device_heartbeat():
    """Simple heartbeat endpoint to check device connectivity"""
    try:
        device = request.device

        # Device last_seen is already updated by authenticate_device decorator

        return (
            jsonify(
                {
                    "message": "Heartbeat received",
                    "device_id": device.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "online",
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error processing heartbeat: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Heartbeat failed",
                    "message": "An error occurred while processing heartbeat",
                }
            ),
            500,
        )
# REMOVED: GET /api/v1/devices/config - DeviceConfiguration model no longer exists
# REMOVED: POST /api/v1/devices/config - Use PUT /api/v1/devices/config instead (RESTful standard)


# REMOVED: GET /api/v1/devices/statuses - Moved to GET /api/v1/admin/devices/statuses
# This is an admin-only endpoint and should be in the admin namespace


@device_bp.route("/<int:device_id>/status", methods=["GET"])
@security_headers_middleware()
@request_metrics_middleware()
def get_device_status_by_id(device_id):
    """
    Get status of a specific device from database
    Requires X-User-ID header for authentication, returns device status with API key
    ---
    tags:
      - Devices
    summary: Get device status
    description: Get status of a specific device (requires user ID, returns API key)
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: integer
        description: Device ID
      - name: X-User-ID
        in: header
        required: true
        schema:
          type: string
        description: User ID (UUID)
        example: adc513e4ab554b3f84900affe582beb8
    responses:
      200:
        description: Device status retrieved successfully (includes API key)
      401:
        description: Authentication required
      403:
        description: Forbidden - device doesn't belong to user
      404:
        description: Device not found
    """
    try:
        # Get X-User-ID from header
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return jsonify({
                "error": "Authentication required",
                "message": "X-User-ID header is required"
            }), 401
        
        # Verify user exists and is active
        user = User.query.filter_by(user_id=user_id, is_active=True).first()
        if not user:
            return jsonify({
                "error": "Authentication failed",
                "message": "Invalid user_id or user is not active"
            }), 401
        
        # Get device from database
        device = Device.query.filter_by(id=device_id).first()
        
        if not device:
            return jsonify({
                "error": "Device not found",
                "message": f"No device found with ID: {device_id}"
            }), 404
        
        # Verify device belongs to the user
        if device.user_id != user.id:
            return jsonify({
                "error": "Forbidden",
                "message": "This device does not belong to the specified user"
            }), 403

        # Build response with device info including API key
        response = {
            "id": device.id,
            "name": device.name,
            "device_type": device.device_type,
            "status": device.status,
            "api_key": device.api_key,  # Include API key in response
            "location": device.location,
            "firmware_version": device.firmware_version,
            "hardware_version": device.hardware_version,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "updated_at": device.updated_at.isoformat() if device.updated_at else None,
        }

        # Get device online status from database
        response["is_online"] = is_device_online(device)
        response["last_seen"] = device.last_seen.isoformat() if device.last_seen else None

        return jsonify({"status": "success", "device": response}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting device status for ID {device_id}: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Status retrieval failed",
                    "message": f"An error occurred while retrieving status for device {device_id}",
                }
            ),
            500,
        )


def is_device_online(device):
    """
    Helper function to check if device is online based on last_seen timestamp
    """
    if not device.last_seen:
        # Device has never been seen
        return False

    # Ensure both datetimes are timezone-aware for comparison
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen
    if last_seen.tzinfo is None:
        # If last_seen is naive, assume it's UTC
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    # Consider device online if last seen in the last 5 minutes
    time_since_last_seen = (now - last_seen).total_seconds()
    is_online = time_since_last_seen < 300  # 5 minutes (300 seconds)

    return is_online


@device_bp.route("/<int:device_id>/groups", methods=["GET"])
@security_headers_middleware()
@request_metrics_middleware()
def get_device_groups(device_id):
    """Get all groups that contain a specific device
    ---
    tags:
      - Devices
    summary: Get device's groups
    description: Get all groups that contain a specific device
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: integer
      - name: X-User-ID
        in: header
        required: true
        schema:
          type: string
    responses:
      200:
        description: Device groups retrieved
      401:
        description: Unauthorized
      403:
        description: Forbidden
      404:
        description: Device not found
    """
    from src.models import DeviceGroupMember
    
    # Get user from header
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 401
    
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({"error": "Invalid user ID"}), 401
    
    # Get device
    device = Device.query.get(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404
    
    if device.user_id != user.id:
        return jsonify({"error": "Forbidden: device doesn't belong to user"}), 403
    
    # Get all group memberships for this device
    memberships = DeviceGroupMember.query.filter_by(device_id=device_id).all()
    
    groups = []
    for membership in memberships:
        group = membership.group
        groups.append({
            'id': group.id,
            'name': group.name,
            'color': group.color,
            'added_at': membership.added_at.isoformat() if membership.added_at else None
        })
    
    return jsonify({
        "status": "success",
        "device_id": device_id,
        "device_name": device.name,
        "groups": groups,
        "total_groups": len(groups)
    }), 200
