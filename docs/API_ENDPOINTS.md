# IoTFlow Backend - Complete API Reference

## Base URL
```
http://localhost:5000
```

## Authentication Methods

| Method | Header | Format | Used For |
|--------|--------|--------|----------|
| **API Key** | `X-API-Key` | `<device_api_key>` | Device endpoints |
| **User ID** | `X-User-ID` | `<user_uuid>` | User-specific endpoints |
| **Admin Token** | `Authorization` | `admin <token>` | Admin endpoints |

---

## 📡 Telemetry Endpoints (Cassandra + Redis + MongoDB)

### Submit Telemetry Data
```http
POST /api/v1/telemetry
```
**Auth:** API Key  
**Storage:** Cassandra (primary), Redis (cache), MongoDB (events)

**Request:**
```json
{
  "data": {
    "temperature": 23.5,
    "humidity": 65.2,
    "pressure": 1013.25
  },
  "metadata": {
    "location": "room1",
    "sensor": "DHT22"
  },
  "timestamp": "2024-12-04T18:00:00Z"  // optional
}
```

**Response:**
```json
{
  "message": "Telemetry data stored successfully",
  "device_id": 1,
  "device_name": "Temperature Sensor",
  "timestamp": "2024-12-04T18:00:00.000Z",
  "stored_in_cassandra": true
}
```

---

### Get Device Telemetry (Historical)
```http
GET /api/v1/telemetry/{device_id}
```
**Auth:** API Key  
**Storage:** Cassandra

**Query Parameters:**
- `start_time` - Start time (default: `-1h`)
  - Relative: `-1h`, `-24h`, `-7d`
  - ISO format: `2024-12-04T18:00:00Z`
- `end_time` - End time (optional)
- `limit` - Max records (default: 1000, m