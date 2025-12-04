"""
Telemetry routes using Cassandra for time-series data
With Redis caching and MongoDB event logging
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
from src.services.cassandra_telemetry import CassandraTelemetryService
from src.services.redis_cache import RedisCacheService
from src.services.mongodb_service import MongoDBService
from src.models import Device

# Create blueprint for telemetry routes
telemetry_bp = Blueprint("telemetry", __name__, url_prefix="/api/v1/telemetry")

# Initialize services
cassandra_service = CassandraTelemetryService()
redis_service = RedisCacheService()
mongodb_service = MongoDBService()


# Helper to get device by API key with Redis caching
def get_authenticated_device(device_id=None):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None, jsonify({"error": "API key required"}), 401
    
    # Try Redis cache first
    cached_device = redis_service.get_device_by_api_key(api_key)
    if cached_device:
        device_id_from_cache = cached_device.get('device_id')
        if device_id is not None and int(device_id_from_cache) != int(device_id):
            return None, jsonify({"error": "Forbidden: device mismatch"}), 403
        
        # Get full device from database
        device = Device.query.get(device_id_from_cache)
        if device:
            return device, None, None
    
    # Cache miss - query database
    device = Device.query.filter_by(api_key=api_key).first()
    if not device:
        return None, jsonify({"error": "Invalid API key"}), 401
    
    # Cache the API key mapping
    redis_service.cache_api_key(api_key, {
        'device_id': device.id,
        'user_id': device.user_id,
        'status': device.status
    }, ttl=3600)
    
    if device_id is not None and int(device.id) != int(device_id):
        return None, jsonify({"error": "Forbidden: device mismatch"}), 403
    
    return device, None, None


@telemetry_bp.route("", methods=["POST"])
def store_telemetry():
    """Store telemetry data in Cassandra
    ---
    tags:
      - Telemetry
    summary: Submit telemetry data
    description: Submit telemetry data from an IoT device (stored in Cassandra)
    security:
      - ApiKeyAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - data
            properties:
              data:
                type: object
                example: {"temperature": 23.5, "humidity": 65.2}
              metadata:
                type: object
              timestamp:
                type: string
                format: date-time
    responses:
      201:
        description: Telemetry data stored successfully
      401:
        description: Unauthorized - invalid API key
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Get API key from headers (with Redis caching)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "API key required"}), 401

        # Check Redis cache first
        cached_device = redis_service.get_device_by_api_key(api_key)
        if cached_device:
            device = Device.query.get(cached_device['device_id'])
        else:
            # Cache miss - query database
            device = Device.query.filter_by(api_key=api_key).first()
            if device:
                # Cache the API key mapping
                redis_service.cache_api_key(api_key, {
                    'device_id': device.id,
                    'user_id': device.user_id,
                    'status': device.status
                }, ttl=3600)
        
        if not device:
            return jsonify({"error": "Invalid API key"}), 401

        telemetry_data = data.get("data", {})
        metadata = data.get("metadata", {})
        timestamp_str = data.get("timestamp")

        if not telemetry_data:
            return jsonify({"error": "Telemetry data is required"}), 400

        # Parse timestamp if provided
        timestamp = None
        if timestamp_str:
            try:
                if timestamp_str.endswith("Z"):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                return jsonify({"error": "Invalid timestamp format. Use ISO 8601 format."}), 400

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Store in Cassandra (primary storage)
        cassandra_success = cassandra_service.write_telemetry_with_user(
            device_id=device.id,
            user_id=device.user_id,
            data=telemetry_data,
            timestamp=timestamp
        )

        # Update Redis cache with latest values
        if cassandra_success:
            redis_service.cache_latest_telemetry(device.id, telemetry_data, ttl=600)
            redis_service.set_device_online(device.id)
            redis_service.update_last_seen(device.id)

        # Update device last_seen in PostgreSQL
        device.update_last_seen()

        # Log event to MongoDB (async, non-blocking)
        try:
            mongodb_service.log_event({
                'event_type': 'telemetry.submitted',
                'device_id': device.id,
                'user_id': device.user_id,
                'timestamp': timestamp,
                'details': {
                    'measurements': list(telemetry_data.keys()),
                    'count': len(telemetry_data)
                }
            })
        except Exception as e:
            current_app.logger.warning(f"Failed to log event to MongoDB: {e}")

        if cassandra_success:
            current_app.logger.info(f"Telemetry stored for device {device.name} (ID: {device.id})")

            return jsonify({
                "message": "Telemetry data stored successfully",
                "device_id": device.id,
                "device_name": device.name,
                "timestamp": timestamp.isoformat(),
                "stored_in_cassandra": True
            }), 201
        else:
            return jsonify({
                "error": "Failed to store telemetry data",
                "message": "Cassandra may not be available. Check logs for details.",
            }), 500

    except Exception as e:
        current_app.logger.error(f"Error storing telemetry: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/<int:device_id>", methods=["GET"])
def get_device_telemetry(device_id):
    """Get telemetry data for a specific device from Cassandra
    ---
    tags:
      - Telemetry
    summary: Get device telemetry
    description: Retrieve telemetry data for a specific device from Cassandra
    security:
      - ApiKeyAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: integer
      - name: start_time
        in: query
        schema:
          type: string
          default: "-1h"
      - name: end_time
        in: query
        schema:
          type: string
      - name: limit
        in: query
        schema:
          type: integer
          default: 1000
    responses:
      200:
        description: Telemetry data retrieved from Cassandra
    """
    device, err, code = get_authenticated_device(device_id)
    if err:
        return err, code
    try:
        telemetry_data = cassandra_service.get_device_telemetry(
            device_id=device_id,
            start_time=request.args.get("start_time", "-1h"),
            end_time=request.args.get("end_time"),
            limit=min(int(request.args.get("limit", 1000)), 10000),
        )
        return jsonify({
            "device_id": device_id,
            "device_name": device.name,
            "device_type": device.device_type,
            "start_time": request.args.get("start_time", "-1h"),
            "data": telemetry_data,
            "count": len(telemetry_data),
            "cassandra_available": cassandra_service.is_available(),
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting telemetry: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/<int:device_id>/latest", methods=["GET"])
def get_device_latest_telemetry(device_id):
    """Get the latest telemetry data for a device (Redis cache first, then Cassandra)
    ---
    tags:
      - Telemetry
    summary: Get latest telemetry
    description: Get the most recent telemetry data for a device (cached in Redis)
    security:
      - ApiKeyAuth: []
    parameters:
      - name: device_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Latest telemetry data
    """
    device, err, code = get_authenticated_device(device_id)
    if err:
        return err, code
    try:
        # Try Redis cache first
        latest_data = redis_service.get_latest_telemetry(device_id)
        
        # If not in cache, get from Cassandra
        if not latest_data:
            latest_data = cassandra_service.get_latest_telemetry(device_id)
            
            # Cache it for next time
            if latest_data:
                redis_service.cache_latest_telemetry(device_id, latest_data, ttl=600)
        
        if latest_data:
            return jsonify({
                "device_id": device_id,
                "device_name": device.name,
                "device_type": device.device_type,
                "latest_data": latest_data,
                "cassandra_available": cassandra_service.is_available(),
            }), 200
        else:
            return jsonify({
                "device_id": device_id,
                "device_name": device.name,
                "message": "No telemetry data found",
                "cassandra_available": cassandra_service.is_available(),
            }), 404
    except Exception as e:
        current_app.logger.error(f"Error getting latest telemetry: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/<int:device_id>/aggregated", methods=["GET"])
def get_device_aggregated_telemetry(device_id):
    """Get aggregated telemetry data for a device"""
    device, err, code = get_authenticated_device(device_id)
    if err:
        return err, code
    try:
        field = request.args.get("field", "temperature")
        aggregation = request.args.get("aggregation", "mean")
        window = request.args.get("window", "1h")
        start_time = request.args.get("start_time", "-24h")
        valid_aggregations = [
            "mean",
            "sum",
            "count",
            "min",
            "max",
            "first",
            "last",
        ]
        if aggregation not in valid_aggregations:
            return (
                jsonify(
                    {
                        "error": "Invalid aggregation function",
                        "valid_functions": valid_aggregations,
                    }
                ),
                400,
            )
        aggregated_data = postgres_service.get_device_aggregated_data(
            device_id=str(device_id),
            field=field,
            aggregation=aggregation,
            window=window,
            start_time=start_time,
        )
        return (
            jsonify(
                {
                    "device_id": device_id,
                    "device_name": device.name,
                    "device_type": device.device_type,
                    "field": field,
                    "aggregation": aggregation,
                    "window": window,
                    "start_time": start_time,
                    "data": aggregated_data,
                    "count": len(aggregated_data),
                    "postgres_available": postgres_service.is_available(),
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.error(f"Error getting aggregated telemetry: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/<int:device_id>", methods=["DELETE"])
def delete_device_telemetry(device_id):
    """Delete telemetry data for a device within a time range"""
    device, err, code = get_authenticated_device(device_id)
    if err:
        return err, code
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify({"error": "Request body required with start_time and stop_time"}),
                400,
            )
        start_time = data.get("start_time")
        stop_time = data.get("stop_time")
        if not start_time or not stop_time:
            return jsonify({"error": "start_time and stop_time are required"}), 400
        success = postgres_service.delete_device_data(
            device_id=str(device_id), 
            start_time=start_time, 
            stop_time=stop_time
        )
        if success:
            current_app.logger.info(f"Telemetry data deleted for device {device.name} (ID: {device_id})")
            return (
                jsonify(
                    {
                        "message": f"Telemetry data deleted for device {device.name}",
                        "device_id": device_id,
                        "start_time": start_time,
                        "stop_time": stop_time,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "error": "Failed to delete telemetry data",
                        "message": "PostgreSQL may not be available. Check logs for details.",
                    }
                ),
                500,
            )
    except Exception as e:
        current_app.logger.error(f"Error deleting telemetry: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/status", methods=["GET"])
def get_telemetry_status():
    """Get PostgreSQL telemetry service status and statistics"""
    try:
        postgres_available = postgres_service.is_available()

        # Get basic statistics
        total_devices = Device.query.count()

        return (
            jsonify(
                {
                    "postgres_available": postgres_available,
                    "backend": "PostgreSQL",
                    "total_devices": total_devices,
                    "status": "healthy" if postgres_available else "unavailable",
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error getting telemetry status: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@telemetry_bp.route("/user/<user_id>", methods=["GET"])
def get_user_telemetry(user_id):
    """Get telemetry data for all devices belonging to a user
    ---
    tags:
      - Telemetry
    summary: Get user's telemetry data
    description: Get telemetry data for all devices belonging to a user (requires user authentication or admin)
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
      - name: limit
        in: query
        schema:
          type: integer
          default: 100
      - name: start_time
        in: query
        schema:
          type: string
          default: "-24h"
      - name: end_time
        in: query
        schema:
          type: string
    responses:
      200:
        description: User telemetry data
      401:
        description: Unauthorized
      403:
        description: Forbidden
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
                    "message": "You can only view your own telemetry data"
                }), 403
        
        # Verify user exists
        from src.models import User
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({
                "error": "User not found",
                "message": f"No user found with ID: {user_id}"
            }), 404

        # Parse query parameters
        limit = min(int(request.args.get("limit", 100)), 1000)
        start_time = request.args.get("start_time", "-24h")
        end_time = request.args.get("end_time")

        # Get telemetry data from PostgreSQL for all user's devices
        try:
            telemetry_data = postgres_service.get_user_telemetry(
                user_id=str(user.id),  # Use internal user ID
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

            # Get telemetry count for the user
            telemetry_count = postgres_service.get_user_telemetry_count(
                user_id=str(user.id),  # Use internal user ID
                start_time=start_time
            )

        except Exception as e:
            current_app.logger.error(f"Error querying user telemetry from PostgreSQL: {str(e)}")
            telemetry_data = []
            telemetry_count = 0

        return (
            jsonify(
                {
                    "status": "success",
                    "user_id": user_id,
                    "telemetry": telemetry_data,
                    "count": len(telemetry_data),
                    "total_count": telemetry_count,
                    "limit": limit,
                    "start_time": start_time,
                    "end_time": end_time,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error retrieving user telemetry: {str(e)}")
        return (
            jsonify(
                {
                    "error": "Telemetry retrieval failed",
                    "message": "An error occurred while retrieving user telemetry data",
                }
            ),
            500,
        )
