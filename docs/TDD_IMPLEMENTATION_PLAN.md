# TDD Implementation Plan for NoSQL Services

## Overview

Following Test-Driven Development (TDD) approach:
1. ✅ **Write tests first** (DONE)
2. ⏳ **Implement services to pass tests** (NEXT)
3. ⏳ **Refactor and optimize** (AFTER)

## Test Coverage

### 1. Cassandra Telemetry Service Tests
**File:** `tests/test_cassandra_service.py`

**Test Classes:**
- `TestCassandraConnection` - Connection and availability (4 tests)
- `TestTelemetryWrite` - Writing telemetry data (7 tests)
- `TestTelemetryRead` - Reading telemetry data (5 tests)
- `TestAggregatedData` - Aggregated data operations (3 tests)
- `TestUserTelemetry` - User-centric queries (2 tests)
- `TestDataDeletion` - Data deletion (2 tests)
- `TestDeviceMeasurements` - Measurement catalog (2 tests)
- `TestTimeRangeParsing` - Time parsing utilities (4 tests)
- `TestBatchOperations` - Batch writes (2 tests)
- `TestErrorHandling` - Error handling (4 tests)
- `TestPerformance` - Performance tests (2 tests)

**Total:** 37 tests

### 2. Redis Cache Service Tests
**File:** `tests/test_redis_service.py`

**Test Classes:**
- `TestRedisConnection` - Connection and availability (3 tests)
- `TestDeviceCache` - Device caching (4 tests)
- `TestAPIKeyCache` - API key caching (3 tests)
- `TestDeviceStatus` - Device online/offline status (5 tests)
- `TestLatestTelemetry` - Latest telemetry caching (4 tests)
- `TestRateLimiting` - Rate limiting (4 tests)
- `TestSessionCache` - User session caching (3 tests)
- `TestAlerts` - Alert caching (4 tests)
- `TestPubSub` - Pub/Sub functionality (4 tests)
- `TestStatistics` - Statistics and metrics (3 tests)
- `TestBulkOperations` - Bulk operations (2 tests)
- `TestCacheInvalidation` - Cache invalidation (2 tests)
- `TestErrorHandling` - Error handling (3 tests)
- `TestPerformance` - Performance tests (2 tests)
- `TestTTLManagement` - TTL management (3 tests)

**Total:** 49 tests

### 3. MongoDB Service Tests
**File:** `tests/test_mongodb_service.py`

**Test Classes:**
- `TestMongoDBConnection` - Connection and availability (3 tests)
- `TestDeviceConfigs` - Device configuration CRUD (5 tests)
- `TestEventLogs` - Event logging (5 tests)
- `TestAlerts` - Alert management (6 tests)
- `TestAnalytics` - Analytics and reporting (3 tests)
- `TestUserPreferences` - User preferences (3 tests)
- `TestDeviceMetadata` - Device metadata and tags (6 tests)
- `TestAggregationPipeline` - Aggregation queries (2 tests)
- `TestBulkOperations` - Bulk operations (2 tests)
- `TestIndexes` - Index management (2 tests)
- `TestErrorHandling` - Error handling (3 tests)
- `TestPerformance` - Performance tests (2 tests)

**Total:** 42 tests

## Implementation Order

### Phase 1: Service Skeletons (Day 1)
Create basic service classes with connection logic:

1. **CassandraTelemetryService** (`src/services/cassandra_telemetry.py`)
   - Connection setup
   - Session management
   - Basic availability check

2. **RedisCacheService** (`src/services/redis_cache.py`)
   - Connection setup
   - Client initialization
   - Basic availability check

3. **MongoDBService** (`src/services/mongodb_service.py`)
   - Connection setup
   - Database initialization
   - Basic availability check

**Goal:** Pass connection tests

### Phase 2: Core Functionality (Day 2-3)

#### Cassandra Service
- Implement write operations
- Implement read operations
- Time range parsing
- Latest telemetry

#### Redis Service
- Device caching
- API key caching
- Latest telemetry caching
- Device status tracking

#### MongoDB Service
- Device configs CRUD
- Event logging
- Alert management

**Goal:** Pass 70% of tests

### Phase 3: Advanced Features (Day 4-5)

#### Cassandra Service
- Aggregated data
- User telemetry queries
- Batch operations
- Data deletion

#### Redis Service
- Rate limiting
- Session management
- Pub/Sub
- Cache invalidation

#### MongoDB Service
- Analytics reports
- User preferences
- Device metadata
- Aggregation pipelines

**Goal:** Pass 90% of tests

### Phase 4: Optimization & Error Handling (Day 6)
- Error handling
- Connection retry logic
- Performance optimization
- Edge case handling

**Goal:** Pass 100% of tests

### Phase 5: Integration (Day 7)
- Update existing routes to use new services
- Add configuration management
- Update initialization scripts
- Integration testing

## Running Tests

### Run All Tests
```bash
# Run all NoSQL service tests
pytest tests/test_cassandra_service.py tests/test_redis_service.py tests/test_mongodb_service.py -v

# Run with coverage
pytest tests/test_*_service.py --cov=src/services --cov-report=html
```

### Run Individual Service Tests
```bash
# Cassandra tests only
pytest tests/test_cassandra_service.py -v

# Redis tests only
pytest tests/test_redis_service.py -v

# MongoDB tests only
pytest tests/test_mongodb_service.py -v
```

### Run Specific Test Class
```bash
# Test only connection
pytest tests/test_cassandra_service.py::TestCassandraConnection -v

# Test only write operations
pytest tests/test_cassandra_service.py::TestTelemetryWrite -v
```

### Run with Markers
```bash
# Run only fast tests (skip performance tests)
pytest tests/test_*_service.py -m "not slow" -v

# Run only integration tests
pytest tests/test_*_service.py -m integration -v
```

## Test Environment Setup

### 1. Start Databases
```bash
# Start all databases
docker compose up -d

# Wait for services to be ready
docker compose ps

# Check health
docker compose logs postgres
docker compose logs cassandra
docker compose logs redis
docker compose logs mongodb
```

### 2. Initialize Databases
```bash
# Initialize Cassandra keyspace
docker compose exec cassandra cqlsh -f /scripts/cassandra-init.cql

# MongoDB is auto-initialized via mongo-init.js

# PostgreSQL
python init_db.py
```

### 3. Install Test Dependencies
```bash
# Install with poetry
poetry install --with dev

# Or with pip
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

## Dependencies to Add

### Python Packages
```toml
[tool.poetry.dependencies]
cassandra-driver = "^3.28.0"
redis = "^5.0.0"
pymongo = "^4.6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.2"
pytest-cov = "^4.1.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.12.0"
```

### Update requirements.txt
```txt
cassandra-driver>=3.28.0,<4.0.0
redis>=5.0.0,<6.0.0
pymongo>=4.6.0,<5.0.0
```

## TDD Workflow

### Red-Green-Refactor Cycle

1. **RED** - Run tests (they should fail)
   ```bash
   pytest tests/test_cassandra_service.py::TestCassandraConnection::test_cassandra_is_available -v
   # Expected: FAILED (not implemented yet)
   ```

2. **GREEN** - Write minimal code to pass
   ```python
   # src/services/cassandra_telemetry.py
   class CassandraTelemetryService:
       def is_available(self):
           return True  # Minimal implementation
   ```

3. **REFACTOR** - Improve code quality
   ```python
   # Add proper connection logic
   def is_available(self):
       try:
           self.session.execute("SELECT now() FROM system.local")
           return True
       except Exception:
           return False
   ```

4. **Repeat** for next test

## Success Criteria

### Phase 1 Complete
- [ ] All connection tests pass
- [ ] Services can connect to databases
- [ ] Health checks work

### Phase 2 Complete
- [ ] Core CRUD operations work
- [ ] Basic caching works
- [ ] Event logging works
- [ ] 70% test coverage

### Phase 3 Complete
- [ ] Advanced features implemented
- [ ] Aggregations work
- [ ] Pub/Sub works
- [ ] 90% test coverage

### Phase 4 Complete
- [ ] All error handling in place
- [ ] Performance tests pass
- [ ] 100% test coverage

### Phase 5 Complete
- [ ] Integration tests pass
- [ ] API routes updated
- [ ] Documentation complete
- [ ] Ready for production

## Next Steps

1. **Install dependencies**
   ```bash
   poetry add cassandra-driver redis pymongo
   ```

2. **Start databases**
   ```bash
   docker compose up -d
   ```

3. **Run tests (expect failures)**
   ```bash
   pytest tests/test_cassandra_service.py -v
   ```

4. **Implement CassandraTelemetryService**
   - Start with connection tests
   - Move to write tests
   - Then read tests
   - Follow TDD cycle

5. **Repeat for Redis and MongoDB**

## Monitoring Progress

Track test results:
```bash
# Generate coverage report
pytest tests/test_*_service.py --cov=src/services --cov-report=term-missing

# Generate HTML report
pytest tests/test_*_service.py --cov=src/services --cov-report=html
open htmlcov/index.html
```

## Notes

- Tests are written to be **independent** - each test can run in isolation
- Tests use **fixtures** for setup/teardown
- Tests include **cleanup** to avoid data pollution
- Tests cover **happy path** and **error cases**
- Tests include **performance benchmarks**
- Tests are **documented** with clear descriptions

## Resources

- [Cassandra Python Driver Docs](https://docs.datastax.com/en/developer/python-driver/)
- [Redis Python Client Docs](https://redis-py.readthedocs.io/)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
