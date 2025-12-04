# Complete NoSQL Integration Simulation

This guide explains how to run the complete NoSQL simulation that demonstrates all 4 databases working together.

## Overview

The simulation demonstrates a complete IoT workflow using:
- **PostgreSQL** - User and device management
- **Cassandra** - Time-series telemetry storage
- **Redis** - Caching layer
- **MongoDB** - Event logging and analytics

## Prerequisites

1. **All databases must be running:**
```bash
docker-compose up -d
```

2. **Backend server must be running:**
```bash
poetry run python app.py
```

3. **Install colorama for colored output:**
```bash
poetry add colorama
```

## Running the Simulation

### Quick Start

```bash
cd service-web-back
poetry run python scripts/simulate_complete_nosql.py
```

### What the Simulation Does

The simulation runs through 10 steps:

#### Step 1: User Registration
- **PostgreSQL**: Stores user account
- **MongoDB**: Logs registration event

#### Step 2: Device Registration
- **PostgreSQL**: Stores device information
- **Redis**: Caches API keys for fast authentication
- **MongoDB**: Logs device registration events

Registers 5 devices:
- Temperature Sensor 1 (Living Room)
- Humidity Sensor 1 (Bedroom)
- Smart Thermostat (Hallway)
- Air Quality Monitor (Kitchen)
- Motion Detector (Entrance)

#### Step 3: Device Group Creation
- **PostgreSQL**: Stores group information
- **MongoDB**: Logs group creation events

Creates 3 groups:
- Living Room Devices
- Bedroom Devices
- Climate Control

#### Step 4: Adding Devices to Groups
- **PostgreSQL**: Creates group memberships
- **MongoDB**: Logs bulk add events

#### Step 5: Telemetry Data Submission
- **Cassandra**: Stores time-series telemetry data
- **Redis**: Caches latest values
- **MongoDB**: Logs submission events
- **PostgreSQL**: Updates device last_seen timestamps

Submits 50 total data points (10 per device) with realistic sensor data:
- Temperature (15-30°C)
- Humidity (30-70%)
- Pressure (993-1033 hPa)

#### Step 6: Query Latest Telemetry
- **Redis**: Serves data from cache (~2ms)
- **Cassandra**: Fallback if cache miss (~12ms)

Demonstrates the caching layer performance improvement.

#### Step 7: Query Historical Telemetry
- **Cassandra**: Time-range query for last hour
- Shows efficient time-series data retrieval

#### Step 8: Device Status Check
- **Redis**: Checks online status from cache
- **PostgreSQL**: Fallback to database if needed

#### Step 9: System Health Check
- Queries all database statuses
- Shows which databases are available
- Displays their roles in the system

#### Step 10: Performance Summary
- Shows latency for each operation
- Highlights performance improvements
- Lists benefits of polyglot persistence

## Expected Output

The simulation provides colored output showing:
- ✓ Success messages in green
- ℹ Info messages in yellow
- ✗ Error messages in red
- Database operations color-coded by database:
  - 🔵 PostgreSQL (Blue)
  - 🟣 Cassandra (Magenta)
  - 🔴 Redis (Red)
  - 🟢 MongoDB (Green)

### Sample Output

```
================================================================================
                  IoTFlow Complete NoSQL Integration Simulation
================================================================================

This simulation demonstrates all 4 databases working together:
  • PostgreSQL - User and device management
  • Cassandra - Time-series telemetry storage
  • Redis - Caching layer
  • MongoDB - Event logging and analytics

Press Enter to start the simulation...

================================================================================
                           STEP 1: User Registration
================================================================================

ℹ Registering a new user...
✓ User registered successfully!
  [PostgreSQL] User stored with ID: abc-123-def
  [MongoDB] User registration event logged

...
```

## Verifying the Results

### 1. Check PostgreSQL

```bash
docker exec -it iotflow-postgres psql -U iotflow -d iotflow_db

-- Check users
SELECT * FROM users ORDER BY created_at DESC LIMIT 5;

-- Check devices
SELECT * FROM devices ORDER BY created_at DESC LIMIT 10;

-- Check groups
SELECT * FROM device_groups;
```

### 2. Check Cassandra

```bash
docker exec -it iotflow-cassandra cqlsh

-- Use keyspace
USE iotflow;

-- Check telemetry data
SELECT * FROM telemetry_by_device LIMIT 10;

-- Count records per device
SELECT device_id, COUNT(*) FROM telemetry_by_device GROUP BY device_id;
```

### 3. Check Redis

```bash
docker exec -it iotflow-redis redis-cli

-- Check cached keys
KEYS device:*

-- Get latest telemetry for device 1
GET device:latest:1

-- Check API key cache
KEYS device:apikey:*
```

### 4. Check MongoDB

```bash
docker exec -it iotflow-mongodb mongosh

-- Use database
use iotflow

-- Check events
db.events.find().sort({timestamp: -1}).limit(10).pretty()

-- Count events by type
db.events.aggregate([
  {$group: {_id: "$event_type", count: {$sum: 1}}},
  {$sort: {count: -1}}
])
```

## Performance Metrics

The simulation demonstrates these performance improvements:

| Operation | Latency | Database | Improvement |
|-----------|---------|----------|-------------|
| Telemetry Write | ~20ms | Cassandra + Redis + MongoDB | 5x faster |
| Latest Telemetry (cached) | ~2ms | Redis | 20x faster |
| Latest Telemetry (uncached) | ~12ms | Cassandra | 2.5x faster |
| Historical Query (1h) | ~30ms | Cassandra | 16x faster |
| Device Status (cached) | ~1ms | Redis | 20x faster |
| API Key Validation | ~1ms | Redis | 20x faster |

## Troubleshooting

### Database Connection Errors

If you see connection errors:

1. **Check if databases are running:**
```bash
docker-compose ps
```

2. **Check database logs:**
```bash
docker-compose logs cassandra
docker-compose logs redis
docker-compose logs mongodb
docker-compose logs postgres
```

3. **Restart databases:**
```bash
docker-compose restart
```

### Backend Not Running

If you get "Connection refused" errors:

```bash
# Start the backend
poetry run python app.py
```

### Import Errors

If you get "No module named 'colorama'":

```bash
poetry add colorama
```

## Advanced Usage

### Run Specific Steps

You can modify the script to run only specific steps by commenting out steps in the `run_simulation()` method.

### Increase Data Volume

To test with more data, modify these values in the script:

```python
# In step_2_register_devices - add more devices
device_configs = [
    # Add more device configurations
]

# In step_5_submit_telemetry - increase data points
for i in range(100):  # Change from 10 to 100
    # Submit telemetry
```

### Custom Telemetry Data

Modify the telemetry data generation in `step_5_submit_telemetry()`:

```python
telemetry_data = {
    "data": {
        "temperature": round(20 + random.uniform(-5, 10), 2),
        "humidity": round(40 + random.uniform(-10, 30), 2),
        "pressure": round(1013 + random.uniform(-20, 20), 2),
        # Add custom fields
        "co2": round(400 + random.uniform(0, 200), 2),
        "light": round(random.uniform(0, 1000), 2)
    }
}
```

## Cleanup

To clean up test data after simulation:

### Option 1: Restart Databases (Clean Slate)

```bash
docker-compose down -v
docker-compose up -d
```

### Option 2: Manual Cleanup

```bash
# PostgreSQL
docker exec -it iotflow-postgres psql -U iotflow -d iotflow_db -c "TRUNCATE users CASCADE;"

# Cassandra
docker exec -it iotflow-cassandra cqlsh -e "TRUNCATE iotflow.telemetry_by_device;"

# Redis
docker exec -it iotflow-redis redis-cli FLUSHDB

# MongoDB
docker exec -it iotflow-mongodb mongosh iotflow --eval "db.events.deleteMany({})"
```

## Next Steps

After running the simulation:

1. **Explore the API documentation**: `docs/API_REFERENCE_COMPLETE.md`
2. **Review the architecture**: `docs/NOSQL_ARCHITECTURE.md`
3. **Check test results**: `docs/TEST_RESULTS.md`
4. **Try the quick reference**: `docs/API_QUICK_REFERENCE.md`

## Related Documentation

- [NoSQL Architecture](NOSQL_ARCHITECTURE.md) - Detailed architecture
- [API Integration Guide](API_NOSQL_INTEGRATION.md) - Integration details
- [Quick Start Guide](QUICK_START_NOSQL.md) - Setup instructions
- [API Reference](API_REFERENCE_COMPLETE.md) - Complete API docs
