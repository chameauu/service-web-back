# NoSQL Multi-Database Architecture

## Overview

IoTFlow Backend uses a polyglot persistence approach, leveraging multiple databases optimized for specific use cases.

## Database Strategy

### 1. PostgreSQL - Relational Core
**Purpose:** Structured data with relationships and ACID requirements

**Tables:**
- `users` - User accounts and authentication
- `devices` - Device registry and ownership
- `device_groups` - Device organization
- `device_group_members` - Many-to-many relationships

**Why PostgreSQL:**
- Strong consistency for user/device relationships
- ACID transactions for critical operations
- Foreign key constraints
- Complex joins for reporting

---

### 2. Cassandra - Time-Series Telemetry
**Purpose:** High-volume, write-heavy telemetry data storage

**Keyspaces & Tables:**
```cql
-- Telemetry by device and time
CREATE TABLE telemetry.device_data (
    device_id int,
    timestamp timestamp,
    measurement_name text,
    numeric_value double,
    text_value text,
    metadata map<text, text>,
    PRIMARY KEY ((device_id), timestamp, measurement_name)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- Telemetry by user (for multi-device queries)
CREATE TABLE telemetry.user_data (
    user_id int,
    device_id int,
    timestamp timestamp,
    measurement_name text,
    numeric_value double,
    PRIMARY KEY ((user_id), timestamp, device_id, measurement_name)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- Aggregated data (hourly/daily rollups)
CREATE TABLE telemetry.aggregated_data (
    device_id int,
    measurement_name text,
    time_bucket timestamp,
    aggregation_type text,
    value double,
    count int,
    PRIMARY KEY ((device_id, measurement_name), time_bucket, aggregation_type)
) WITH CLUSTERING ORDER BY (time_bucket DESC);
```

**Use Cases:**
- Store raw telemetry data (millions of writes/sec)
- Time-range queries (last hour, last 24h, last 7d)
- Historical data retention
- Multi-datacenter replication

**Why Cassandra:**
- Linear scalability for writes
- Tunable consistency
- Time-series optimized with clustering
- No single point of failure
- Excellent for append-only data

---

### 3. Redis - Caching & Real-Time
**Purpose:** In-memory caching and real-time operations

**Data Structures:**

```redis
# Device API Key Cache (Hash)
device:apikey:{api_key} -> {device_id, user_id, status}
TTL: 1 hour

# Device Status (Hash)
device:status:{device_id} -> {status, last_seen, is_online}
TTL: 5 minutes

# Latest Telemetry (Hash)
device:latest:{device_id} -> {temperature: 23.5, humidity: 65, ...}
TTL: 10 minutes

# Rate Limiting (Counter)
ratelimit:device:{device_id}:{window} -> count
TTL: window duration

# User Session Cache (Hash)
session:{user_id} -> {username, email, is_admin, ...}
TTL: 30 minutes

# Online Devices (Sorted Set)
devices:online -> {device_id: last_seen_timestamp}

# Real-time Alerts (List)
alerts:{device_id} -> [alert1, alert2, ...]
TTL: 24 hours

# Pub/Sub Channels
channel:device:{device_id}:telemetry
channel:user:{user_id}:notifications
channel:system:alerts
```

**Use Cases:**
- Cache frequently accessed data
- Real-time device online/offline status
- Rate limiting and throttling
- Session management
- Pub/Sub for real-time updates
- Leaderboards and rankings
- Temporary data storage

**Why Redis:**
- Sub-millisecond latency
- Atomic operations
- Built-in TTL support
- Pub/Sub for real-time
- Reduces database load

---

### 4. MongoDB - Flexible Documents
**Purpose:** Schema-flexible document storage

**Collections:**

```javascript
// Device Configurations
db.device_configs.insertOne({
    device_id: 123,
    user_id: 456,
    config_version: "2.1.0",
    settings: {
        sampling_rate: 60,
        thresholds: {
            temperature: { min: 0, max: 50, unit: "celsius" },
            humidity: { min: 20, max: 80, unit: "percent" }
        },
        alerts: [
            { type: "threshold", field: "temperature", condition: ">", value: 45 },
            { type: "offline", duration: 300 }
        ],
        reporting: {
            interval: 3600,
            aggregations: ["mean", "min", "max"]
        }
    },
    created_at: ISODate(),
    updated_at: ISODate()
});

// Event Logs & Audit Trail
db.event_logs.insertOne({
    event_id: ObjectId(),
    event_type: "device.status_changed",
    device_id: 123,
    user_id: 456,
    timestamp: ISODate(),
    details: {
        old_status: "active",
        new_status: "maintenance",
        reason: "scheduled_maintenance",
        initiated_by: "admin"
    },
    metadata: {
        ip_address: "192.168.1.100",
        user_agent: "IoTFlow/1.0"
    }
});

// Device Alerts & Notifications
db.alerts.insertOne({
    alert_id: ObjectId(),
    device_id: 123,
    user_id: 456,
    alert_type: "threshold_exceeded",
    severity: "warning",
    message: "Temperature exceeded threshold",
    details: {
        measurement: "temperature",
        value: 52.3,
        threshold: 50,
        unit: "celsius"
    },
    status: "active",
    acknowledged: false,
    created_at: ISODate(),
    resolved_at: null
});

// Analytics & Reports
db.analytics.insertOne({
    report_id: ObjectId(),
    report_type: "device_health",
    device_id: 123,
    user_id: 456,
    period: {
        start: ISODate("2024-01-01"),
        end: ISODate("2024-01-31")
    },
    metrics: {
        uptime_percentage: 99.2,
        total_data_points: 44640,
        average_temperature: 23.5,
        alerts_triggered: 3,
        maintenance_events: 1
    },
    generated_at: ISODate()
});

// User Preferences
db.user_preferences.insertOne({
    user_id: 456,
    preferences: {
        dashboard: {
            default_view: "grid",
            widgets: ["device_status", "recent_alerts", "telemetry_chart"],
            refresh_interval: 30
        },
        notifications: {
            email: true,
            push: false,
            alert_types: ["critical", "warning"]
        },
        timezone: "America/New_York",
        language: "en"
    },
    updated_at: ISODate()
});

// Device Metadata & Tags
db.device_metadata.insertOne({
    device_id: 123,
    tags: ["production", "critical", "building-a"],
    location: {
        type: "Point",
        coordinates: [-73.935242, 40.730610],
        address: "123 Main St, New York, NY"
    },
    custom_fields: {
        department: "Operations",
        cost_center: "CC-1234",
        warranty_expiry: ISODate("2025-12-31")
    },
    notes: [
        { text: "Installed on 2024-01-15", author: "admin", date: ISODate() }
    ]
});
```

**Use Cases:**
- Device configuration management
- Event logging and audit trails
- Alert and notification history
- Analytics and reporting data
- User preferences and settings
- Device metadata and tags
- Complex nested data structures
- Schema evolution without migrations

**Why MongoDB:**
- Flexible schema for evolving requirements
- Rich query language
- Geospatial queries for location data
- Aggregation pipeline for analytics
- Document model matches JSON APIs
- Easy to add new fields

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer (Flask)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │   Cassandra  │  │    Redis     │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                            │
│  │   MongoDB    │                                            │
│  │   Service    │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                          │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │  Cassandra   │  │    Redis     │      │
│  │              │  │              │  │              │      │
│  │ Users        │  │ Telemetry    │  │ Cache        │      │
│  │ Devices      │  │ Time-Series  │  │ Sessions     │      │
│  │ Groups       │  │ Historical   │  │ Real-time    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐                                            │
│  │   MongoDB    │                                            │
│  │              │                                            │
│  │ Configs      │                                            │
│  │ Events       │                                            │
│  │ Alerts       │                                            │
│  │ Analytics    │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow Examples

### 1. Device Registration
```
POST /api/v1/devices/register
├─> PostgreSQL: Insert device record
├─> MongoDB: Create default config
└─> Redis: Cache device info
```

### 2. Telemetry Submission
```
POST /api/v1/telemetry
├─> Redis: Check rate limit
├─> Redis: Update latest values
├─> Cassandra: Write telemetry data (async)
├─> Redis: Update device last_seen
└─> MongoDB: Check alert rules (async)
```

### 3. Get Device Status
```
GET /api/v1/devices/status
├─> Redis: Check cache
│   └─> Cache HIT: Return cached data
│   └─> Cache MISS:
│       ├─> PostgreSQL: Get device info
│       ├─> Redis: Get latest telemetry
│       └─> Redis: Cache result
```

### 4. Query Historical Data
```
GET /api/v1/telemetry/{device_id}?start=-24h
├─> Redis: Check API key cache
├─> Cassandra: Query time-series data
└─> Return results
```

### 5. Get Device Config
```
GET /api/v1/devices/{id}/config
├─> Redis: Check cache
│   └─> Cache MISS:
│       ├─> MongoDB: Get config document
│       └─> Redis: Cache config
```

## Performance Optimizations

### Write Path
1. **Telemetry writes** → Cassandra (optimized for writes)
2. **Latest values** → Redis (in-memory, fast reads)
3. **Event logs** → MongoDB (async, non-blocking)

### Read Path
1. **Check Redis cache** first
2. **Query appropriate database** on cache miss
3. **Update cache** with result

### Caching Strategy
- **Hot data** (latest telemetry): Redis, TTL 5-10 min
- **Device info**: Redis, TTL 1 hour
- **User sessions**: Redis, TTL 30 min
- **Config data**: Redis, TTL 1 hour

## Consistency Model

### Strong Consistency
- User authentication (PostgreSQL)
- Device ownership (PostgreSQL)
- Financial/billing data (PostgreSQL)

### Eventual Consistency
- Telemetry data (Cassandra)
- Event logs (MongoDB)
- Analytics (MongoDB)

### Cache Invalidation
- Write-through for critical data
- TTL-based for telemetry
- Event-driven for config changes

## Scalability Strategy

### Horizontal Scaling
- **Cassandra**: Add nodes to cluster
- **Redis**: Redis Cluster or Sentinel
- **MongoDB**: Sharding by user_id or device_id
- **PostgreSQL**: Read replicas for queries

### Data Retention
- **Redis**: TTL-based expiration
- **Cassandra**: TTL on telemetry (e.g., 90 days)
- **MongoDB**: Archive old events to cold storage
- **PostgreSQL**: Keep core data indefinitely

## Monitoring & Observability

### Metrics to Track
- Database response times
- Cache hit/miss ratios
- Write throughput (Cassandra)
- Connection pool usage
- Query performance
- Data volume growth

### Health Checks
- `/health` endpoint checks all databases
- Circuit breakers for database failures
- Graceful degradation when services unavailable

## Migration Strategy

### Phase 1: Add NoSQL Services
1. Deploy Cassandra, Redis, MongoDB
2. Create service classes
3. Run in parallel with PostgreSQL

### Phase 2: Gradual Migration
1. New telemetry → Cassandra
2. Enable Redis caching
3. Move configs → MongoDB

### Phase 3: Optimize
1. Remove PostgreSQL telemetry table
2. Tune cache TTLs
3. Optimize queries

## Benefits Summary

| Database   | Strength                    | Use Case                |
|------------|-----------------------------|-------------------------|
| PostgreSQL | ACID, Relations             | Users, Devices, Groups  |
| Cassandra  | Write scalability           | Telemetry, Time-series  |
| Redis      | Speed, Real-time            | Cache, Sessions, Status |
| MongoDB    | Flexibility, Rich queries   | Configs, Events, Logs   |

## Trade-offs

### Complexity
- **Pro**: Optimized for each use case
- **Con**: More systems to manage

### Consistency
- **Pro**: Eventual consistency for high throughput
- **Con**: Potential data lag

### Operations
- **Pro**: Each DB can scale independently
- **Con**: More monitoring and maintenance

## Conclusion

This polyglot persistence architecture provides:
- **Performance**: Right tool for each job
- **Scalability**: Horizontal scaling where needed
- **Flexibility**: Schema evolution without downtime
- **Reliability**: No single point of failure
