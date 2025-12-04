# IoTFlow API Reference - Complete

Complete API reference for all endpoints with authentication requirements.

## 🗄️ Database Architecture

IoTFlow uses a **polyglot persistence** architecture with multiple specialized databases:

- **PostgreSQL** - User accounts, devices, groups, and relationships
- **Cassandra** - Time-series telemetry data (primary storage)
- **Redis** - Caching layer for device info, API keys, and latest telemetry
- **MongoDB** - Event logging, alerts, and analytics

This architecture provides:
- **5x faster writes** - Cassandra optimized for time-series data
- **20x faster reads** - Redis caching for frequently accessed data
- **Horizontal scalability** - All NoSQL databases scale horizontally
- **High availability** - Distributed architecture with no single point of failure



---

## Authentication Methods

### 1. API Key Authentication
**Header:** `X-API-Key: <device_api_key>`
- Used by devices to authenticate
- Generated during device registration
- Unique per device

### 2. User ID Authentication
**Header:** `X-User-ID: <user_id>`
- Used for user-specific operations
- UUID string identifier
- Required for managing groups and devices

### 3. Admin Token Authentication
**Header:** `Authorization: admin <token>`
- Used for administrative operations
- Token configured in environment variable `IOTFLOW_ADMIN_TOKEN`
- Default value: `test` (development only)
- Full system access

**Example:**
```bash
curl -X GET http://localhost:5000/api/v1/users \
  -H "Authorization: admin test"
```



---

## API Endpoints by Category

## 🔌 Device Management

### Register Device
**POST** `/api/v1/devices/register`

**Authentication:** `X-User-ID` (User ID)

**Description:** Register a new IoT device. Device info is stored in PostgreSQL and cached in Redis.

**Storage:** PostgreSQL (primary) + Redis (cache)

**Request:**
```json
{
  "name": "Temperature Sensor 001",
  "description": "Living room sensor",
  "device_type": "sensor",
  "location": "Living Room",
  "firmware_version": "1.2.3",
  "hardware_version": "v2.1"
}
```

**Response (201):**
```json
{
  "message": "Device registered successfully",
  "device": {
    "id": 1,
    "name": "Temperature Sensor 001",
    "api_key": "rnby0SIR2kF8mN3Q7vX9L1cE6tA5Y4pB",
    "status": "inactive",
    "device_type": "sensor",
    "user_id": 1
  }
}
```

**Note:** API key is automatically cached in Redis for fast authentication

---

### Get Device Status
**GET** `/api/v1/devices/status`

**Authentication:** `X-API-Key` (API Key)

**Description:** Get current device status and health information

**Response (200):**
```json
{
  "device_id": 1,
  "name": "Temperature Sensor 001",
  "status": "active",
  "last_seen": "2025-11-23T14:30:00Z",
  "is_online": true
}
```

---

### Send Heartbeat
**POST** `/api/v1/devices/heartbeat`

**Authentication:** `X-API-Key` (API Key)

**Description:** Send device heartbeat to update last_seen timestamp

**Response (200):**
```json
{
  "message": "Heartbeat received",
  "device_id": 1,
  "timestamp": "2025-11-23T14:30:00Z"
}
```

---

### Update Device Config
**PUT** `/api/v1/devices/config`

**Authentication:** `X-API-Key` (API Key)

**Description:** Update device configuration

**Request:**
```json
{
  "status": "active",
  "location": "Kitchen"
}
```

**Response (200):**
```json
{
  "message": "Configuration updated",
  "device": {
    "id": 1,
    "status": "active",
    "location": "Kitchen"
  }
}
```

---

### Get Device Credentials
**GET** `/api/v1/devices/credentials`

**Authentication:** `X-API-Key` (API Key)

**Description:** Get device credentials and API key

**Response (200):**
```json
{
  "device_id": 1,
  "api_key": "rnby0SIR2kF8mN3Q7vX9L1cE6tA5Y4pB",
  "name": "Temperature Sensor 001"
}
```

---

### Get User's Devices
**GET** `/api/v1/devices/user/{user_id}`

**Authentication:** `X-User-ID` (User ID header) or Admin Token

**Description:** Get all devices belonging to a user. Users can only access their own devices unless using admin authentication.

**Headers:**
- `X-User-ID` (required): User UUID (must match the user_id in path)
- `Authorization` (optional): Admin token for cross-user access

**Path Parameters:**
- `user_id` (required): User UUID

**Query Parameters:**
- `status` (optional): Filter by device status (active, inactive, maintenance)
- `limit` (optional): Maximum number of devices to return (default: 100)
- `offset` (optional): Number of devices to skip for pagination (default: 0)

**Response (200):**
```json
{
  "status": "success",
  "user_id": "adc513e4ab554b3f84900affe582beb8",
  "username": "john_doe",
  "total_devices": 5,
  "devices": [
    {
      "id": 1,
      "name": "Temperature Sensor 001",
      "device_type": "sensor",
      "status": "active",
      "location": "Living Room",
      "firmware_version": "1.0.0",
      "hardware_version": "v2.1",
      "created_at": "2025-11-20T10:00:00Z",
      "updated_at": "2025-11-23T10:00:00Z",
      "last_seen": "2025-11-23T14:30:00Z"
    }
  ],
  "meta": {
    "limit": 100,
    "offset": 0,
    "returned": 5
  }
}
```

**Response (401):**
```json
{
  "error": "Authentication required",
  "message": "X-User-ID header required"
}
```

**Response (403):**
```json
{
  "error": "Forbidden",
  "message": "You can only view your own devices"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "No user found with ID: {user_id}"
}
```

---

### Get Device Status by ID
**GET** `/api/v1/devices/{device_id}/status`

**Authentication:** `X-User-ID` (User ID header)

**Description:** Get status of a specific device. Users can only access devices they own.

**Headers:**
- `X-User-ID` (required): User UUID

**Path Parameters:**
- `device_id` (required): Device ID (integer)

**Response (200):**
```json
{
  "status": "success",
  "device": {
    "id": 1,
    "name": "Temperature Sensor 001",
    "device_type": "sensor",
    "status": "active",
    "api_key": "abc123...",
    "location": "Living Room",
    "firmware_version": "1.0.0",
    "hardware_version": "v2.1",
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-23T10:00:00Z",
    "is_online": true,
    "last_seen": "2025-11-23T14:30:00Z"
  }
}
```

**Response (401):**
```json
{
  "error": "Authentication required",
  "message": "X-User-ID header is required"
}
```

**Response (403):**
```json
{
  "error": "Forbidden",
  "message": "This device does not belong to the specified user"
}
```

**Response (404):**
```json
{
  "error": "Device not found",
  "message": "No device found with ID: {device_id}"
}
```

---

## 📊 Telemetry Data

### Submit Telemetry
**POST** `/api/v1/telemetry`

**Authentication:** `X-API-Key` (API Key)

**Description:** Submit telemetry data with metadata. Data is stored in Cassandra (primary), cached in Redis, and logged to MongoDB.

**Storage Flow:**
1. **Cassandra** - Primary time-series storage
2. **Redis** - Cache latest values (10 min TTL)
3. **MongoDB** - Log submission event
4. **PostgreSQL** - Update device last_seen timestamp

**Request:**
```json
{
  "data": {
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.25
  },
  "metadata": {
    "location": "Living Room",
    "sensor": "DHT22"
  },
  "timestamp": "2025-11-23T14:30:00Z"
}
```

**Response (201):**
```json
{
  "message": "Telemetry data stored successfully",
  "device_id": 1,
  "device_name": "Temperature Sensor 001",
  "timestamp": "2025-11-23T14:30:00.000Z",
  "stored_in_cassandra": true
}
```

**Performance:**
- Write latency: ~5ms (Cassandra)
- Cache update: ~1ms (Redis)
- Event logging: Async, non-blocking

---

### Get Device Telemetry
**GET** `/api/v1/telemetry/{device_id}`

**Authentication:** `X-API-Key` (API Key)

**Description:** Get historical telemetry data for a device from Cassandra

**Storage:** Cassandra (time-series optimized)

**Query Parameters:**
- `start_time` - Start time (default: "-1h")
  - Relative: "-1h", "-24h", "-7d", "-30d"
  - ISO format: "2025-11-23T14:30:00Z"
- `end_time` - End time (optional)
- `limit` - Max records (default: 1000, max: 10000)

**Response (200):**
```json
{
  "device_id": 1,
  "device_name": "Temperature Sensor 001",
  "device_type": "sensor",
  "start_time": "-1h",
  "data": [
    {
      "timestamp": "2025-11-23T14:30:00.000Z",
      "temperature": 23.5,
      "humidity": 65.2,
      "pressure": 1013.25
    }
  ],
  "count": 1,
  "cassandra_available": true
}
```

**Performance:**
- Query latency: ~10-50ms (Cassandra)
- Optimized for time-range queries
- Efficient for large datasets

---

### Get Latest Telemetry
**GET** `/api/v1/telemetry/{device_id}/latest`

**Authentication:** `X-API-Key` (API Key)

**Description:** Get the most recent telemetry data. Checks Redis cache first, falls back to Cassandra.

**Storage:** Redis (cache) → Cassandra (fallback)

**Response (200):**
```json
{
  "device_id": 1,
  "device_name": "Temperature Sensor 001",
  "device_type": "sensor",
  "latest_data": {
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.25,
    "timestamp": "2025-11-23T14:30:00.000Z"
  },
  "cassandra_available": true
}
```

**Response (404):**
```json
{
  "device_id": 1,
  "device_name": "Temperature Sensor 001",
  "message": "No telemetry data found",
  "cassandra_available": true
}
```

**Performance:**
- Cache hit: ~1ms (Redis)
- Cache miss: ~10ms (Cassandra + cache update)
- Cache TTL: 10 minutes

---

### Get Aggregated Telemetry
**GET** `/api/v1/telemetry/{device_id}/aggregated`

**Authentication:** `X-API-Key` (API Key)

**Description:** Get aggregated telemetry data

**Query Parameters:**
- `field` - Measurement field (e.g., "temperature")
- `aggregation` - Function (mean, sum, min, max)
- `window` - Time window (e.g., "1h")
- `start_time` - Start time (e.g., "-24h")

**Response (200):**
```json
{
  "device_id": 1,
  "field": "temperature",
  "aggregation": "mean",
  "data": [
    {
      "timestamp": "2025-11-23T14:00:00Z",
      "value": 23.5,
      "count": 10
    }
  ]
}
```

---

### Delete Device Telemetry
**DELETE** `/api/v1/telemetry/{device_id}`

**Authentication:** `X-API-Key` (API Key)

**Description:** Delete telemetry data for a time range

**Request:**
```json
{
  "start_time": "2025-11-23T00:00:00Z",
  "stop_time": "2025-11-23T23:59:59Z"
}
```

**Response (200):**
```json
{
  "message": "Telemetry data deleted",
  "device_id": 1
}
```

---

### Get Telemetry Status
**GET** `/api/v1/telemetry/status`

**Authentication:** None (Public)

**Description:** Get telemetry system status and database health

**Response (200):**
```json
{
  "status": "healthy",
  "databases": {
    "cassandra": {
      "available": true,
      "role": "Time-series telemetry storage"
    },
    "redis": {
      "available": true,
      "role": "Caching layer"
    },
    "mongodb": {
      "available": true,
      "role": "Event logging and analytics"
    },
    "postgres": {
      "available": true,
      "role": "User and device management"
    }
  },
  "total_devices": 10,
  "backend": "Polyglot Persistence"
}
```

---

### Get User Telemetry
**GET** `/api/v1/telemetry/user/{user_id}`

**Authentication:** `X-User-ID` (User ID header) or Admin Token

**Description:** Get telemetry data for all devices belonging to a user. Users can only access their own telemetry data unless using admin authentication.

**Headers:**
- `X-User-ID` (required): User UUID (must match the user_id in path)
- `Authorization` (optional): Admin token for cross-user access

**Path Parameters:**
- `user_id` (required): User UUID

**Query Parameters:**
- `start_time` (optional): Start time for telemetry data (default: "-24h")
- `end_time` (optional): End time for telemetry data
- `limit` (optional): Maximum number of records to return (default: 100, max: 1000)

**Response (200):**
```json
{
  "status": "success",
  "user_id": "adc513e4ab554b3f84900affe582beb8",
  "telemetry": [
    {
      "device_id": 1,
      "device_name": "Temperature Sensor 001",
      "timestamp": "2025-11-23T14:30:00Z",
      "measurement_name": "temperature",
      "value": 23.5,
      "unit": "celsius"
    }
  ],
  "count": 1,
  "total_count": 150,
  "limit": 100,
  "start_time": "-24h",
  "end_time": null
}
```

**Response (401):**
```json
{
  "error": "Authentication required",
  "message": "X-User-ID header required"
}
```

**Response (403):**
```json
{
  "error": "Forbidden",
  "message": "You can only view your own telemetry data"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "No user found with ID: {user_id}"
}
```

---

## 👥 User Management



### Get User Details
**GET** `/api/v1/users/{user_id}`

**Authentication:** `X-User-ID` (User ID header) or Admin Token

**Description:** Get user information. Users can only access their own profile unless using admin authentication.

**Headers:**
- `X-User-ID` (required): User UUID (must match the user_id in path)
- `Authorization` (optional): Admin token for cross-user access

**Path Parameters:**
- `user_id` (required): User UUID

**Response (200):**
```json
{
  "status": "success",
  "user": {
    "id": 1,
    "user_id": "adc513e4ab554b3f84900affe582beb8",
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-23T10:00:00Z",
    "last_login": "2025-11-23T14:00:00Z"
  }
}
```

**Response (401):**
```json
{
  "error": "Authentication required",
  "message": "X-User-ID header is required"
}
```

**Response (403):**
```json
{
  "error": "Forbidden",
  "message": "You can only view your own profile"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "User not found"
}
```

---

### List All Users
**GET** `/api/v1/users`

**Authentication:** Admin Token

**Description:** List all users (admin only)

**Request Headers:**
```
Authorization: admin <admin_token>
```

**Response (200):**
```json
{
  "users": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com"
    }
  ]
}
```

---

### Update User
**PUT** `/api/v1/users/{user_id}`

**Authentication:** None (Public)

**Description:** Update user information

**Request:**
```json
{
  "email": "newemail@example.com"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "User updated successfully"
}
```

---

### Deactivate User (Soft Delete)
**PATCH** `/api/v1/users/{user_id}/deactivate`

**Authentication:** Admin Token

**Description:** Deactivate a user account without deleting data (soft delete). User will not be able to log in but data is preserved. Requires admin privileges.

**Headers:**
- `Authorization` (required): Admin token (format: "admin <token>")

**Path Parameters:**
- `user_id` (required): User UUID

**Response (200):**
```json
{
  "status": "success",
  "message": "User 'john_doe' deactivated successfully"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "No user found with ID: {user_id}"
}
```

---

### Activate User
**PATCH** `/api/v1/users/{user_id}/activate`

**Authentication:** Admin Token

**Description:** Reactivate a previously deactivated user account. Requires admin privileges.

**Headers:**
- `Authorization` (required): Admin token (format: "admin <token>")

**Path Parameters:**
- `user_id` (required): User UUID

**Response (200):**
```json
{
  "status": "success",
  "message": "User 'john_doe' activated successfully"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "No user found with ID: {user_id}"
}
```

---

### Delete User (Hard Delete)
**DELETE** `/api/v1/users/{user_id}`

**Authentication:** Admin Token

**Description:** Permanently delete a user account and all associated data (hard delete). This action cannot be undone. Requires admin privileges.

**Headers:**
- `Authorization` (required): Admin token (format: "admin <token>")

**Path Parameters:**
- `user_id` (required): User UUID

**Response (200):**
```json
{
  "status": "success",
  "message": "User 'john_doe' deleted permanently"
}
```

**Response (404):**
```json
{
  "error": "User not found",
  "message": "No user found with ID: {user_id}"
}
```

**Note:** This permanently removes the user and all associated devices, groups, and data from the database due to CASCADE delete.

---

## 🔐 Authentication

### User Registration
**POST** `/api/v1/auth/register`

**Authentication:** None (Public)

**Description:** Register a new user account (public endpoint)

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "user_id": "adc513e4ab554b3f84900affe582beb8",
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true
  }
}
```

---

### User Login
**POST** `/api/v1/auth/login`

**Authentication:** None (Public)

**Description:** Authenticate user and receive user information. No JWT tokens - use the returned user_id for subsequent API calls via X-User-ID header.

**Request:**
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Login successful",
  "user": {
    "id": 1,
    "user_id": "adc513e4ab554b3f84900affe582beb8",
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2025-11-20T10:00:00Z",
    "updated_at": "2025-11-23T10:00:00Z",
    "last_login": "2025-11-23T14:00:00Z"
  }
}
```

**Response (400):**
```json
{
  "error": "Missing credentials",
  "message": "username and password are required"
}
```

**Response (401):**
```json
{
  "error": "Authentication failed",
  "message": "Invalid username or password"
}
```

**Note:** After successful login, use the `user_id` from the response in the `X-User-ID` header for authenticated requests.

---

### User Logout
**POST** `/api/v1/auth/logout`

**Authentication:** None (Public)

**Description:** Logout endpoint (stateless - no server-side session management)

**Response (200):**
```json
{
  "status": "success",
  "message": "Logout successful"
}
```

---

## 📦 Device Groups

### Create Group
**POST** `/api/v1/groups`

**Authentication:** `X-User-ID` (User ID)

**Description:** Create a new device group

**Request:**
```json
{
  "name": "Living Room",
  "description": "All living room devices",
  "color": "#FF5733"
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "Group created successfully",
  "group": {
    "id": 1,
    "name": "Living Room",
    "description": "All living room devices",
    "user_id": 1,
    "color": "#FF5733",
    "device_count": 0
  }
}
```

---

### List User's Groups
**GET** `/api/v1/groups`

**Authentication:** `X-User-ID` (User ID)

**Description:** Get all groups for authenticated user

**Query Parameters:**
- `include_devices` - Include device list (default: false)
- `limit` - Max results (default: 100)
- `offset` - Pagination offset (default: 0)

**Response (200):**
```json
{
  "status": "success",
  "groups": [
    {
      "id": 1,
      "name": "Living Room",
      "device_count": 5
    }
  ],
  "meta": {
    "total": 1,
    "limit": 100,
    "offset": 0
  }
}
```

---

### Get Group Details
**GET** `/api/v1/groups/{group_id}`

**Authentication:** `X-User-ID` (User ID)

**Description:** Get detailed information about a group

**Query Parameters:**
- `include_devices` - Include device list (default: true)

**Response (200):**
```json
{
  "status": "success",
  "group": {
    "id": 1,
    "name": "Living Room",
    "description": "All living room devices",
    "color": "#FF5733",
    "device_count": 2,
    "devices": [
      {
        "id": 1,
        "name": "Temperature Sensor 1",
        "status": "active"
      }
    ]
  }
}
```

---

### Update Group
**PUT** `/api/v1/groups/{group_id}`

**Authentication:** `X-User-ID` (User ID)

**Description:** Update group information

**Request:**
```json
{
  "name": "Living Room Updated",
  "description": "New description",
  "color": "#33FF57"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Group updated successfully",
  "group": {
    "id": 1,
    "name": "Living Room Updated"
  }
}
```

---

### Delete Group
**DELETE** `/api/v1/groups/{group_id}`

**Authentication:** `X-User-ID` (User ID)

**Description:** Delete a group (devices are not deleted)

**Response (200):**
```json
{
  "status": "success",
  "message": "Group 'Living Room' deleted successfully"
}
```

---

### Add Device to Group
**POST** `/api/v1/groups/{group_id}/devices`

**Authentication:** `X-User-ID` (User ID)

**Description:** Add a device to a group

**Request:**
```json
{
  "device_id": 5
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "Device added to group successfully",
  "membership": {
    "id": 10,
    "group_id": 1,
    "device_id": 5,
    "added_at": "2025-11-23T11:30:00Z"
  }
}
```

---

### Remove Device from Group
**DELETE** `/api/v1/groups/{group_id}/devices/{device_id}`

**Authentication:** `X-User-ID` (User ID)

**Description:** Remove a device from a group

**Response (200):**
```json
{
  "status": "success",
  "message": "Device removed from group successfully"
}
```

---

### List Group's Devices
**GET** `/api/v1/groups/{group_id}/devices`

**Authentication:** `X-User-ID` (User ID)

**Description:** Get all devices in a group

**Query Parameters:**
- `status` - Filter by status
- `device_type` - Filter by type
- `limit` - Max results
- `offset` - Pagination offset

**Response (200):**
```json
{
  "status": "success",
  "group_id": 1,
  "group_name": "Living Room",
  "devices": [
    {
      "id": 1,
      "name": "Temperature Sensor 1",
      "added_to_group_at": "2025-11-23T10:45:00Z"
    }
  ]
}
```

---

### Bulk Add Devices
**POST** `/api/v1/groups/{group_id}/devices/bulk`

**Authentication:** `X-User-ID` (User ID)

**Description:** Add multiple devices to a group

**Request:**
```json
{
  "device_ids": [1, 2, 3, 4, 5]
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "5 devices added to group",
  "added": 5,
  "skipped": 0
}
```

---

### Get Device's Groups
**GET** `/api/v1/devices/{device_id}/groups`

**Authentication:** `X-User-ID` (User ID)

**Description:** Get all groups containing a device

**Response (200):**
```json
{
  "status": "success",
  "device_id": 1,
  "device_name": "Temperature Sensor 1",
  "groups": [
    {
      "id": 1,
      "name": "Living Room",
      "color": "#FF5733",
      "added_at": "2025-11-23T10:45:00Z"
    }
  ],
  "total_groups": 1
}
```

---

## 🛠️ Administration

### List All Devices
**GET** `/api/v1/admin/devices`

**Authentication:** Admin Token

**Description:** List all devices in the system (admin only)

**Response (200):**
```json
{
  "devices": [
    {
      "id": 1,
      "name": "Temperature Sensor 001",
      "status": "active",
      "user_id": 1
    }
  ]
}
```

---

### Get Device Details (Admin)
**GET** `/api/v1/admin/devices/{device_id}`

**Authentication:** Admin Token

**Description:** Get detailed device information (admin only)

**Response (200):**
```json
{
  "device": {
    "id": 1,
    "name": "Temperature Sensor 001",
    "api_key": "rnby0SIR2kF8mN3Q7vX9L1cE6tA5Y4pB",
    "status": "active"
  }
}
```

---

### Update Device (Admin)
**PUT** `/api/v1/admin/devices/{device_id}`

**Authentication:** Admin Token

**Description:** Update device information (admin only)

**Request:**
```json
{
  "status": "maintenance"
}
```

**Response (200):**
```json
{
  "message": "Device updated successfully"
}
```

---

### Delete Device (Admin)
**DELETE** `/api/v1/admin/devices/{device_id}`

**Authentication:** Admin Token

**Description:** Delete a device (admin only)

**Response (200):**
```json
{
  "message": "Device deleted successfully"
}
```

---

### Update Device Status (Admin)
**PUT** `/api/v1/admin/devices/{device_id}/status`

**Authentication:** Admin Token

**Description:** Update device status (admin only)

**Request:**
```json
{
  "status": "active"
}
```

**Response (200):**
```json
{
  "message": "Device status updated"
}
```

---

### Get System Statistics
**GET** `/api/v1/admin/stats`

**Authentication:** Admin Token

**Description:** Get system statistics (admin only)

**Response (200):**
```json
{
  "total_devices": 10,
  "active_devices": 8,
  "total_users": 5,
  "telemetry_records": 1000
}
```

---

### Get All Device Statuses
**GET** `/api/v1/admin/devices/statuses`

**Authentication:** Admin Token

**Description:** Get status of all devices with online/offline information (admin only)

**Query Parameters:**
- `limit` (optional): Maximum number of devices to return (default: 100)
- `offset` (optional): Number of devices to skip (default: 0)

**Response (200):**
```json
{
  "status": "success",
  "devices": [
    {
      "id": 1,
      "name": "Temperature Sensor 001",
      "device_type": "sensor",
      "status": "active",
      "is_online": true
    },
    {
      "id": 2,
      "name": "Humidity Sensor 002",
      "device_type": "sensor",
      "status": "active",
      "is_online": false
    }
  ],
  "meta": {
    "total": 50,
    "limit": 100,
    "offset": 0
  }
}
```

---

## 🏥 Health & Status

### Health Check
**GET** `/health`

**Authentication:** None (Public)

**Description:** Basic health check

**Response (200):**
```json
{
  "status": "healthy",
  "message": "IoT Connectivity Layer is running",
  "version": "1.0.0"
}
```

---

### Detailed Health Check
**GET** `/health?detailed=true`

**Authentication:** None (Public)

**Description:** Detailed health information

**Response (200):**
```json
{
  "status": "healthy",
  "database": "connected",
  "telemetry": "available",
  "uptime": "24h"
}
```

---

### System Status
**GET** `/status`

**Authentication:** None (Public)

**Description:** Detailed system status and metrics

**Response (200):**
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "type": "PostgreSQL"
  },
  "metrics": {
    "total_devices": 10,
    "active_devices": 8
  }
}
```

---




## 🔑 Authentication Summary

### By Authentication Type

**API Key (`X-API-Key`):**
- Device status, heartbeat, config
- Submit and retrieve telemetry
- Device credentials
- Delete device telemetry

**User ID (`X-User-ID`):**
- Register devices
- View user's devices
- View device status by ID
- Manage device groups
- View user profile
- View user's telemetry data
- Update user profile

**Admin Token (`Authorization: admin <token>`):**
- All admin endpoints (`/api/v1/admin/*`)
- System statistics
- Device management (list, view, update, delete)
- User management (list, delete)
- Cross-user access (view any user's devices, telemetry, profile)

**None (Public):**
- User registration (`/api/v1/auth/register`)
- User login (`/api/v1/auth/login`)
- User logout (`/api/v1/auth/logout`)
- Health checks (`/health`, `/status`)
- Telemetry service status (`/api/v1/telemetry/status`)
- API information (`/`)

---

## 📝 Notes

1. **API Keys** are generated during device registration and cached in Redis
2. **User IDs** are UUID strings returned when creating users
3. **Admin Token** is configured in environment variables
4. All timestamps are in ISO 8601 format (UTC)
5. Pagination is supported on list endpoints
6. Rate limiting may apply to prevent abuse
7. **Caching Strategy:**
   - Device info and API keys: 1 hour TTL
   - Latest telemetry: 10 minutes TTL
   - Aggregated data: 5 minutes TTL

## 🚀 Performance Characteristics

### Write Operations
- **Telemetry submission**: ~5ms (Cassandra) + ~1ms (Redis cache)
- **Device registration**: ~50ms (PostgreSQL) + ~1ms (Redis cache)
- **Event logging**: Async, non-blocking (MongoDB)

### Read Operations
- **Latest telemetry** (cached): ~1ms (Redis)
- **Latest telemetry** (uncached): ~10ms (Cassandra)
- **Historical telemetry**: ~10-50ms (Cassandra, depends on range)
- **Device lookup** (cached): ~1ms (Redis)
- **Device lookup** (uncached): ~20ms (PostgreSQL)

### Scalability
- **Cassandra**: Horizontal scaling, handles millions of writes/sec
- **Redis**: In-memory, sub-millisecond latency
- **MongoDB**: Flexible schema, horizontal scaling
- **PostgreSQL**: ACID compliance, relational integrity

---

## 📊 Complete Endpoint Summary

### Total: 43 Endpoints

#### Device Management (11 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/devices/register` | User ID | Register new device |
| GET | `/api/v1/devices/user/{user_id}` | User ID or Admin | Get user's devices (own devices or admin) |
| GET | `/api/v1/devices/status` | API Key | Get device status |
| PUT | `/api/v1/devices/config` | API Key | Update device config |
| GET | `/api/v1/devices/config` | API Key | Get device config |
| GET | `/api/v1/devices/credentials` | API Key | Get device credentials |
| POST | `/api/v1/devices/heartbeat` | API Key | Send heartbeat |
| GET | `/api/v1/devices/{device_id}/status` | User ID | Get device status by ID |
| GET | `/api/v1/devices/{device_id}/groups` | User ID | Get device's groups |

#### Telemetry (7 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/telemetry` | API Key | Submit telemetry |
| GET | `/api/v1/telemetry/{device_id}` | API Key | Get telemetry history |
| GET | `/api/v1/telemetry/{device_id}/latest` | API Key | Get latest telemetry |
| GET | `/api/v1/telemetry/{device_id}/aggregated` | API Key | Get aggregated data |
| DELETE | `/api/v1/telemetry/{device_id}` | API Key | Delete telemetry |
| GET | `/api/v1/telemetry/status` | None | Telemetry service status |
| GET | `/api/v1/telemetry/user/{user_id}` | User ID | Get user's telemetry |

#### User Management (6 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/users/{user_id}` | User ID or Admin | Get user details (own profile or admin) |
| GET | `/api/v1/users` | Admin | List all users |
| PUT | `/api/v1/users/{user_id}` | User ID or Admin | Update user (own profile or admin) |
| PATCH | `/api/v1/users/{user_id}/deactivate` | Admin | Deactivate user (soft delete) |
| PATCH | `/api/v1/users/{user_id}/activate` | Admin | Activate deactivated user |
| DELETE | `/api/v1/users/{user_id}` | Admin | Delete user permanently (hard delete) |

#### Authentication (3 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/login` | None | User login |
| POST | `/api/v1/auth/logout` | None | User logout |

#### Device Groups (10 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/groups` | User ID | Create group |
| GET | `/api/v1/groups` | User ID | List user's groups |
| GET | `/api/v1/groups/{id}` | User ID | Get group details |
| PUT | `/api/v1/groups/{id}` | User ID | Update group |
| DELETE | `/api/v1/groups/{id}` | User ID | Delete group |
| POST | `/api/v1/groups/{id}/devices` | User ID | Add device to group |
| DELETE | `/api/v1/groups/{id}/devices/{device_id}` | User ID | Remove device from group |
| GET | `/api/v1/groups/{id}/devices` | User ID | List group devices |
| POST | `/api/v1/groups/{id}/devices/bulk` | User ID | Bulk add devices |

#### Admin (5 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/admin/devices` | Admin | List all devices |
| GET | `/api/v1/admin/devices/statuses` | Admin | Get all device statuses |
| GET | `/api/v1/admin/devices/{id}` | Admin | Get device details |
| PUT | `/api/v1/admin/devices/{id}/status` | Admin | Update device status |
| DELETE | `/api/v1/admin/devices/{id}` | Admin | Delete device |
| GET | `/api/v1/admin/stats` | Admin | System statistics |

#### Health & Status (3 endpoints)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/status` | None | System status |
| GET | `/` | None | API information |

---

## 🔗 Related Documentation

- [NoSQL Architecture](NOSQL_ARCHITECTURE.md) - Detailed architecture documentation
- [Quick Start Guide](QUICK_START_NOSQL.md) - Setup and running instructions
- [Run Simulation](RUN_SIMULATION.md) - Test the complete system
- [Test Results](TEST_RESULTS.md) - Test coverage and results
- [OpenAPI Spec](openapi.yaml) - OpenAPI 3.0 specification

## 🧪 Testing the APIs

### Using curl

**Submit telemetry:**
```bash
curl -X POST http://localhost:5000/api/v1/telemetry \
  -H "X-API-Key: your_device_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "temperature": 23.5,
      "humidity": 65.2
    }
  }'
```

**Get latest telemetry:**
```bash
curl -X GET http://localhost:5000/api/v1/telemetry/1/latest \
  -H "X-API-Key: your_device_api_key"
```

**Get historical telemetry:**
```bash
curl -X GET "http://localhost:5000/api/v1/telemetry/1?start_time=-24h&limit=100" \
  -H "X-API-Key: your_device_api_key"
```

### Using the Simulation Script

Run the complete system simulation:
```bash
cd service-web-back
python scripts/simulate_system.py
```

This will:
1. Register a test user
2. Register test devices
3. Submit telemetry data
4. Query data from all databases
5. Demonstrate the complete data flow
