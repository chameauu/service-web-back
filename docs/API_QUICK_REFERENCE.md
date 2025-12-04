# IoTFlow API Quick Reference

## 🔑 Authentication

| Type | Header | Format | Usage |
|------|--------|--------|-------|
| **API Key** | `X-API-Key` | `<device_api_key>` | Device operations |
| **User ID** | `X-User-ID` | `<user_uuid>` | User operations |
| **Admin** | `Authorization` | `admin <token>` | Admin operations |

---

## 📡 Telemetry APIs (Cassandra + Redis + MongoDB)

### Submit Telemetry
```bash
POST /api/v1/telemetry
X-API-Key: {device_api_key}

{
  "data": {"temperature": 23.5, "humidity": 65.2},
  "timestamp": "2025-11-23T14:30:00Z"  # optional
}
```
**Storage:** Cassandra (primary) + Redis (cache) + MongoDB (events)  
**Latency:** ~20ms

### Get Latest Telemetry
```bash
GET /api/v1/telemetry/{device_id}/latest
X-API-Key: {device_api_key}
```
**Storage:** Redis (cache) → Cassandra (fallback)  
**Latency:** ~2ms (cached) / ~12ms (uncached)

### Get Historical Telemetry
```bash
GET /api/v1/telemetry/{device_id}?start_time=-24h&limit=100
X-API-Key: {device_api_key}
```
**Storage:** Cassandra  
**Latency:** ~30ms

---

## 🔌 Device APIs (PostgreSQL + Redis)

### Register Device
```bash
POST /api/v1/devices/register
X-User-ID: {user_uuid}

{
  "name": "Temperature Sensor 001",
  "device_type": "sensor",
  "location": "Living Room"
}
```
**Returns:** Device ID + API Key

### Get Device Status
```bash
GET /api/v1/devices/status
X-API-Key: {device_api_key}
```

### Send Heartbeat
```bash
POST /api/v1/devices/heartbeat
X-API-Key: {device_api_key}
```

### List User's Devices
```bash
GET /api/v1/devices/user/{user_id}
X-User-ID: {user_uuid}
```

---

## 👥 User APIs (PostgreSQL)

### Register User
```bash
POST /api/v1/auth/register

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password"
}
```
**Returns:** User ID (UUID)

### Login
```bash
POST /api/v1/auth/login

{
  "username": "john_doe",
  "password": "secure_password"
}
```
**Returns:** User details (use `user_id` for subsequent requests)

### Get User Details
```bash
GET /api/v1/users/{user_id}
X-User-ID: {user_uuid}
```

---

## 📦 Group APIs (PostgreSQL)

### Create Group
```bash
POST /api/v1/groups
X-User-ID: {user_uuid}

{
  "name": "Living Room",
  "description": "All living room devices",
  "color": "#FF5733"
}
```

### List Groups
```bash
GET /api/v1/groups
X-User-ID: {user_uuid}
```

### Add Device to Group
```bash
POST /api/v1/groups/{group_id}/devices
X-User-ID: {user_uuid}

{
  "device_id": 5
}
```

---

## 🛠️ Admin APIs

### List All Devices
```bash
GET /api/v1/admin/devices
Authorization: admin {token}
```

### Get System Stats
```bash
GET /api/v1/admin/stats
Authorization: admin {token}
```

### Delete Device
```bash
DELETE /api/v1/admin/devices/{device_id}
Authorization: admin {token}
```

---

## 🏥 Health Check

### Basic Health
```bash
GET /health
```

### System Status
```bash
GET /status
```

### Telemetry Status
```bash
GET /api/v1/telemetry/status
```

---

## 🗄️ Database Usage by Endpoint

| Endpoint | PostgreSQL | Cassandra | Redis | MongoDB |
|----------|------------|-----------|-------|---------|
| `POST /telemetry` | ✓ (last_seen) | ✓ (write) | ✓ (cache) | ✓ (event) |
| `GET /telemetry/{id}/latest` | - | ✓ (fallback) | ✓ (read) | - |
| `GET /telemetry/{id}` | - | ✓ (read) | - | - |
| `POST /devices/register` | ✓ (write) | - | ✓ (cache) | - |
| `GET /devices/status` | ✓ (read) | - | ✓ (cache) | - |
| `POST /auth/register` | ✓ (write) | - | - | - |
| `POST /groups` | ✓ (write) | - | - | - |

---

## ⚡ Performance Tips

### 1. Use Latest Endpoint for Real-Time Data
```bash
# Fast (cached in Redis)
GET /api/v1/telemetry/1/latest

# Slower (queries Cassandra)
GET /api/v1/telemetry/1?limit=1
```

### 2. Limit Historical Queries
```bash
# Good - specific time range
GET /api/v1/telemetry/1?start_time=-1h&limit=100

# Bad - unbounded query
GET /api/v1/telemetry/1?limit=10000
```

### 3. Batch Operations
```bash
# Use bulk endpoints when available
POST /api/v1/groups/{id}/devices/bulk
{
  "device_ids": [1, 2, 3, 4, 5]
}
```

---

## 🐛 Common Errors

### 401 Unauthorized
```json
{"error": "API key required"}
```
**Fix:** Add `X-API-Key` header

### 403 Forbidden
```json
{"error": "Forbidden: device mismatch"}
```
**Fix:** Use correct API key for the device

### 404 Not Found
```json
{"error": "Device not found"}
```
**Fix:** Verify device ID exists

### 500 Internal Server Error
```json
{"error": "Failed to store telemetry data"}
```
**Fix:** Check database connectivity

---

## 📊 Response Times (Typical)

| Operation | Latency | Notes |
|-----------|---------|-------|
| Submit telemetry | 20ms | Cassandra write + Redis cache |
| Get latest (cached) | 2ms | Redis only |
| Get latest (uncached) | 12ms | Cassandra + Redis cache |
| Get historical (1h) | 15ms | Cassandra query |
| Get historical (24h) | 30ms | Cassandra query |
| Get historical (7d) | 100ms | Cassandra query |
| Device registration | 50ms | PostgreSQL + Redis |
| API key validation | 1ms | Redis cache |

---

## 🔗 Full Documentation

- **[Complete API Reference](API_REFERENCE_COMPLETE.md)** - All endpoints with examples
- **[NoSQL Integration Guide](API_NOSQL_INTEGRATION.md)** - Architecture deep dive
- **[Quick Start](QUICK_START_NOSQL.md)** - Setup instructions
- **[Run Simulation](RUN_SIMULATION.md)** - Test the system

---

## 💡 Example Workflow

### 1. Register User
```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "pass123"}'

# Response: {"user": {"user_id": "abc-123-def"}}
```

### 2. Register Device
```bash
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "X-User-ID: abc-123-def" \
  -H "Content-Type: application/json" \
  -d '{"name": "Temp Sensor", "device_type": "sensor"}'

# Response: {"device": {"id": 1, "api_key": "xyz789"}}
```

### 3. Submit Telemetry
```bash
curl -X POST http://localhost:5000/api/v1/telemetry \
  -H "X-API-Key: xyz789" \
  -H "Content-Type: application/json" \
  -d '{"data": {"temperature": 23.5}}'

# Response: {"message": "Telemetry data stored successfully"}
```

### 4. Get Latest Data
```bash
curl -X GET http://localhost:5000/api/v1/telemetry/1/latest \
  -H "X-API-Key: xyz789"

# Response: {"latest_data": {"temperature": 23.5, "timestamp": "..."}}
```

---

## 🚀 Testing Script

Save as `test_api.sh`:
```bash
#!/bin/bash

BASE_URL="http://localhost:5000"

# 1. Register user
USER_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "test123"}')

USER_ID=$(echo $USER_RESPONSE | jq -r '.user.user_id')
echo "User ID: $USER_ID"

# 2. Register device
DEVICE_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/devices/register \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Sensor", "device_type": "sensor"}')

DEVICE_ID=$(echo $DEVICE_RESPONSE | jq -r '.device.id')
API_KEY=$(echo $DEVICE_RESPONSE | jq -r '.device.api_key')
echo "Device ID: $DEVICE_ID"
echo "API Key: $API_KEY"

# 3. Submit telemetry
curl -X POST $BASE_URL/api/v1/telemetry \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {"temperature": 23.5, "humidity": 65.2}}'

# 4. Get latest
curl -X GET $BASE_URL/api/v1/telemetry/$DEVICE_ID/latest \
  -H "X-API-Key: $API_KEY"
```

Run with: `bash test_api.sh`
