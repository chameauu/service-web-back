# Quick Start Guide - NoSQL Integration

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
cd service-web-back

# With Poetry (recommended)
poetry add cassandra-driver redis pymongo
poetry install

# Or with pip
pip install cassandra-driver redis pymongo
```

### 2. Start All Databases
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 3. Initialize Databases
```bash
# Wait for Cassandra to be ready (takes ~60 seconds)
sleep 60

# Initialize Cassandra keyspace
docker compose exec cassandra cqlsh -f /docker-entrypoint-initdb.d/cassandra-init.cql

# MongoDB auto-initializes via mongo-init.js
# Redis requires no initialization

# Initialize PostgreSQL
python init_db.py
```

### 4. Run Tests (TDD Approach)
```bash
# Run all tests (will fail initially - that's expected!)
pytest tests/test_cassandra_service.py tests/test_redis_service.py tests/test_mongodb_service.py -v

# Run specific service tests
pytest tests/test_cassandra_service.py -v
pytest tests/test_redis_service.py -v
pytest tests/test_mongodb_service.py -v
```

## 📊 Database Overview

| Database   | Port  | Purpose                          | Data Type              |
|------------|-------|----------------------------------|------------------------|
| PostgreSQL | 5432  | Users, Devices, Groups           | Relational             |
| Cassandra  | 9042  | Telemetry Time-Series            | Wide-Column            |
| Redis      | 6379  | Cache, Sessions, Real-time       | Key-Value              |
| MongoDB    | 27017 | Configs, Events, Alerts          | Document               |

## 🔧 Management Tools

### Access Database UIs
```bash
# Start management tools
docker compose --profile tools up -d

# Access tools:
# - Cassandra Web: http://localhost:3000
# - Redis Commander: http://localhost:8081
# - Mongo Express: http://localhost:8082 (admin/admin)
```

### Direct Database Access
```bash
# Cassandra CQL Shell
docker compose exec cassandra cqlsh

# Redis CLI
docker compose exec redis redis-cli -a iotflowpass

# MongoDB Shell
docker compose exec mongodb mongosh -u iotflow -p iotflowpass

# PostgreSQL
docker compose exec postgres psql -U iotflow -d iotflow
```

## 📝 TDD Workflow

### Step 1: Run Tests (RED)
```bash
# Tests will fail - that's expected!
pytest tests/test_cassandra_service.py::TestCassandraConnection -v
```

### Step 2: Implement Service (GREEN)
```python
# Create src/services/cassandra_telemetry.py
from cassandra.cluster import Cluster

class CassandraTelemetryService:
    def __init__(self):
        self.cluster = Cluster(['localhost'])
        self.session = self.cluster.connect('telemetry')
    
    def is_available(self):
        try:
            self.session.execute("SELECT now() FROM system.local")
            return True
        except:
            return False
```

### Step 3: Run Tests Again
```bash
# Tests should pass now!
pytest tests/test_cassandra_service.py::TestCassandraConnection -v
```

### Step 4: Refactor & Repeat
Continue with next test class...

## 🎯 Implementation Checklist

### Cassandra Service
- [ ] Connection management
- [ ] Write telemetry data
- [ ] Read telemetry data
- [ ] Time range queries
- [ ] Aggregated data
- [ ] User telemetry queries
- [ ] Batch operations
- [ ] Data deletion

### Redis Service
- [ ] Connection management
- [ ] Device caching
- [ ] API key caching
- [ ] Device status tracking
- [ ] Latest telemetry caching
- [ ] Rate limiting
- [ ] Session management
- [ ] Pub/Sub messaging
- [ ] Cache invalidation

### MongoDB Service
- [ ] Connection management
- [ ] Device configs CRUD
- [ ] Event logging
- [ ] Alert management
- [ ] Analytics reports
- [ ] User preferences
- [ ] Device metadata
- [ ] Aggregation queries

## 🧪 Testing Commands

### Run All Tests
```bash
# All NoSQL tests
pytest tests/test_*_service.py -v

# With coverage
pytest tests/test_*_service.py --cov=src/services --cov-report=html

# Fast tests only (skip performance)
pytest tests/test_*_service.py -k "not performance" -v
```

### Run Specific Tests
```bash
# Single test
pytest tests/test_cassandra_service.py::TestTelemetryWrite::test_write_single_measurement -v

# Test class
pytest tests/test_redis_service.py::TestDeviceCache -v

# Pattern matching
pytest tests/test_mongodb_service.py -k "config" -v
```

### Watch Mode (Auto-rerun on changes)
```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw tests/test_cassandra_service.py -- -v
```

## 📦 Service Usage Examples

### Cassandra - Write Telemetry
```python
from src.services.cassandra_telemetry import CassandraTelemetryService

service = CassandraTelemetryService()

# Write telemetry
service.write_telemetry(
    device_id=1,
    data={'temperature': 23.5, 'humidity': 65.2},
    timestamp=datetime.now(timezone.utc)
)

# Read telemetry
data = service.get_device_telemetry(
    device_id=1,
    start_time='-24h',
    limit=1000
)
```

### Redis - Cache Device
```python
from src.services.redis_cache import RedisCacheService

service = RedisCacheService()

# Cache device
service.cache_device(
    device_id=1,
    device_data={'name': 'Sensor 1', 'status': 'active'},
    ttl=3600
)

# Get cached device
device = service.get_device(device_id=1)

# Cache latest telemetry
service.cache_latest_telemetry(
    device_id=1,
    telemetry={'temperature': 23.5},
    ttl=600
)
```

### MongoDB - Device Config
```python
from src.services.mongodb_service import MongoDBService

service = MongoDBService()

# Create config
service.create_device_config({
    'device_id': 1,
    'user_id': 100,
    'config_version': '1.0.0',
    'settings': {
        'sampling_rate': 60,
        'thresholds': {'temperature': {'max': 50}}
    }
})

# Get config
config = service.get_device_config(device_id=1)

# Log event
service.log_event({
    'event_type': 'device.registered',
    'device_id': 1,
    'user_id': 100
})
```

## 🔍 Debugging

### Check Database Connections
```bash
# Test Cassandra
docker compose exec cassandra cqlsh -e "SELECT * FROM system.local;"

# Test Redis
docker compose exec redis redis-cli -a iotflowpass ping

# Test MongoDB
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Test PostgreSQL
docker compose exec postgres pg_isready
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f cassandra
docker compose logs -f redis
docker compose logs -f mongodb
```

### Check Data
```bash
# Cassandra - View telemetry
docker compose exec cassandra cqlsh -e "SELECT * FROM telemetry.device_data LIMIT 10;"

# Redis - View keys
docker compose exec redis redis-cli -a iotflowpass KEYS "*"

# MongoDB - View collections
docker compose exec mongodb mongosh -u iotflow -p iotflowpass --eval "db.device_configs.find().limit(5)"
```

## 🐛 Troubleshooting

### Cassandra Not Starting
```bash
# Check logs
docker compose logs cassandra

# Increase memory if needed (edit docker-compose.yml)
MAX_HEAP_SIZE: 1G
HEAP_NEWSIZE: 200M

# Restart
docker compose restart cassandra
```

### Redis Connection Refused
```bash
# Check if running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli -a iotflowpass ping

# Restart
docker compose restart redis
```

### MongoDB Authentication Failed
```bash
# Check credentials in .env
MONGODB_URI=mongodb://iotflow:iotflowpass@localhost:27017/iotflow?authSource=admin

# Recreate container
docker compose down mongodb
docker compose up -d mongodb
```

### Tests Failing
```bash
# Clean test data
docker compose exec cassandra cqlsh -e "TRUNCATE telemetry.device_data;"
docker compose exec redis redis-cli -a iotflowpass FLUSHDB
docker compose exec mongodb mongosh -u iotflow -p iotflowpass --eval "db.dropDatabase()"

# Reinitialize
python init_db.py
```

## 📚 Next Steps

1. **Implement Services** - Follow TDD approach
2. **Update Routes** - Integrate new services into API
3. **Add Configuration** - Environment-based config
4. **Performance Testing** - Load test with Locust
5. **Documentation** - API docs and examples
6. **Monitoring** - Add metrics and logging

## 🎓 Learning Resources

- **Cassandra**: https://cassandra.apache.org/doc/latest/
- **Redis**: https://redis.io/docs/
- **MongoDB**: https://www.mongodb.com/docs/
- **TDD**: https://testdriven.io/

## 💡 Tips

1. **Start Small** - Implement one service at a time
2. **Follow TDD** - Write tests first, then implement
3. **Use Management Tools** - Visualize your data
4. **Monitor Performance** - Track query times
5. **Cache Wisely** - Use appropriate TTLs
6. **Handle Errors** - Graceful degradation
7. **Document Changes** - Keep README updated

## ✅ Success Indicators

- [ ] All databases running and healthy
- [ ] Tests passing (or failing as expected in TDD)
- [ ] Can write and read data from each database
- [ ] Management tools accessible
- [ ] No connection errors in logs
- [ ] Ready to implement services!

---

**Ready to start?** Run `docker compose up -d` and begin with the first test! 🚀
