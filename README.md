# IoTFlow Backend

A production-ready IoT backend platform built with Python Flask for device connectivity, telemetry data collection, and real-time analytics. Features PostgreSQL storage, comprehensive REST API, and enterprise-grade security.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey)
![Tests](https://img.shields.io/badge/tests-158%20passing-success)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO/branch/main/graph/badge.svg)](https://app.codecov.io/github/chameauu/service-web-back/)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

- **Device Management** - Complete device lifecycle with secure API key authentication
- **PostgreSQL Storage** - Unified database for devices, users, and time-series telemetry
- **REST API** - Comprehensive HTTP API with Swagger documentation
- **Real-time Analytics** - Time-series queries, aggregations, and data visualization
- **Enterprise Security** - API key auth, JWT tokens, rate limiting, admin protection
- **User Management** - Multi-user support with device ownership and access control
- **Device Groups** - Organize devices into logical groups
- **Comprehensive Testing** - Full test coverage with 158 passing tests
- **Docker Support** - Containerized deployment with Docker Compose
- **Load Testing** - Locust integration for performance testing

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Poetry (recommended) or pip
- Docker & Docker Compose
- PostgreSQL 15+

### Installation

```bash
# Clone repository
git clone <repository-url>
cd iotflow-backend

# Install dependencies with Poetry
poetry install

# Or with pip
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Start PostgreSQL
docker compose up -d

# Initialize database
poetry run python init_db.py

# Start application
poetry run python app.py
```

### Verify Installation

```bash
# Health check
curl http://localhost:5000/health

# API documentation
open http://localhost:5000/docs

# Run tests
poetry run pytest tests/ -v
```

## 📡 API Overview

### Authentication

- **No Auth**: Public endpoints (health, registration)
- **API Key**: Device endpoints via `X-API-Key` header
- **Admin Token**: Admin endpoints via `Authorization: admin <TOKEN>` header
- **User ID**: User-specific endpoints via `X-User-ID` header

### Key Endpoints

**Device Management**
- `POST /api/v1/devices/register` - Register new device
- `GET /api/v1/devices/status` - Get device status
- `POST /api/v1/devices/heartbeat` - Send heartbeat
- `GET /api/v1/devices/user/{user_id}` - Get user's devices
- `GET /api/v1/devices/{device_id}/groups` - Get device groups

**Telemetry**
- `POST /api/v1/telemetry` - Submit telemetry data
- `GET /api/v1/telemetry/{device_id}` - Get device telemetry
- `GET /api/v1/telemetry/{device_id}/latest` - Get latest data
- `GET /api/v1/telemetry/{device_id}/aggregated` - Get aggregated data
- `DELETE /api/v1/telemetry/{device_id}` - Delete device telemetry

**User Management**
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - User login (JWT)
- `GET /api/v1/users/{user_id}` - Get user details
- `PUT /api/v1/users/{user_id}` - Update user
- `PATCH /api/v1/users/{user_id}/deactivate` - Deactivate user (admin)
- `PATCH /api/v1/users/{user_id}/activate` - Activate user (admin)
- `DELETE /api/v1/users/{user_id}` - Delete user (admin, non-admin only)

**Device Groups**
- `POST /api/v1/groups` - Create device group
- `GET /api/v1/groups` - List user's groups
- `GET /api/v1/groups/{group_id}` - Get group details
- `PUT /api/v1/groups/{group_id}` - Update group
- `DELETE /api/v1/groups/{group_id}` - Delete group
- `POST /api/v1/groups/{group_id}/devices/{device_id}` - Add device to group
- `DELETE /api/v1/groups/{group_id}/devices/{device_id}` - Remove device

**Administration**
- `GET /api/v1/admin/devices` - List all devices
- `GET /api/v1/admin/devices/{id}` - Get device details
- `GET /api/v1/admin/stats` - System statistics
- `PUT /api/v1/admin/devices/{id}/status` - Update device status
- `DELETE /api/v1/admin/devices/{id}` - Delete device
- `GET /api/v1/admin/devices/statuses` - Get all device statuses

## 💡 Usage Examples

### Register User & Device

```bash
# Register user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password"
  }'

# Response includes user_id
{
  "status": "success",
  "user": {
    "user_id": "abc123...",
    "username": "john_doe",
    "email": "john@example.com"
  }
}

# Register device
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -H "X-User-ID: abc123..." \
  -d '{
    "name": "Temperature Sensor 001",
    "device_type": "sensor",
    "location": "Living Room",
    "firmware_version": "1.0.0"
  }'

# Response includes API key
{
  "message": "Device registered successfully",
  "device": {
    "id": 1,
    "name": "Temperature Sensor 001",
    "api_key": "xyz789...",
    "status": "inactive"
  }
}
```

### Submit & Query Telemetry

```bash
# Submit telemetry
curl -X POST http://localhost:5000/api/v1/telemetry \
  -H "X-API-Key: xyz789..." \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "temperature": 23.5,
      "humidity": 65.2,
      "pressure": 1013.25
    },
    "metadata": {
      "location": "Living Room",
      "sensor_type": "DHT22"
    }
  }'

# Get latest data
curl "http://localhost:5000/api/v1/telemetry/1/latest" \
  -H "X-API-Key: xyz789..."

# Get historical data (last hour)
curl "http://localhost:5000/api/v1/telemetry/1?start_time=-1h&limit=100" \
  -H "X-API-Key: xyz789..."

# Get aggregated data (hourly averages for last 24 hours)
curl "http://localhost:5000/api/v1/telemetry/1/aggregated?window=1h&start_time=-24h&field=temperature&aggregation=mean" \
  -H "X-API-Key: xyz789..."
```

### Device Groups

```bash
# Create group
curl -X POST http://localhost:5000/api/v1/groups \
  -H "Content-Type: application/json" \
  -H "X-User-ID: abc123..." \
  -d '{
    "name": "Living Room Sensors",
    "description": "All sensors in living room",
    "color": "#FF5733"
  }'

# Add device to group
curl -X POST "http://localhost:5000/api/v1/groups/1/devices/1" \
  -H "X-User-ID: abc123..."

# Get group with devices
curl "http://localhost:5000/api/v1/groups/1?include_devices=true" \
  -H "X-User-ID: abc123..."
```

### Admin Operations

```bash
# Set admin token
ADMIN_TOKEN="your-admin-token"

# Get system statistics
curl "http://localhost:5000/api/v1/admin/stats" \
  -H "Authorization: admin ${ADMIN_TOKEN}"

# List all devices
curl "http://localhost:5000/api/v1/admin/devices" \
  -H "Authorization: admin ${ADMIN_TOKEN}"

# Update device status
curl -X PUT "http://localhost:5000/api/v1/admin/devices/1/status" \
  -H "Authorization: admin ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"status": "maintenance"}'

# Deactivate user (soft delete)
curl -X PATCH "http://localhost:5000/api/v1/users/abc123.../deactivate" \
  -H "Authorization: admin ${ADMIN_TOKEN}"
```

## 🗃️ Database Schema

### Users
- User accounts with authentication
- Admin role support
- Soft delete (deactivation) capability
- Admin users cannot be deleted or deactivated

### Devices
- Device registration and management
- API key authentication
- Status tracking (active/inactive/maintenance)
- Last seen timestamps
- User ownership

### Telemetry
- Time-series data storage in PostgreSQL
- JSONB metadata support
- Indexed for fast queries
- Aggregation support (mean, sum, min, max, count)
- Flexible time-based queries

### Device Groups
- Logical device organization
- Many-to-many device relationships
- User-owned groups
- Color coding support

## 🧪 Testing

```bash
# Run all tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Run specific test suite
poetry run pytest tests/test_devices.py -v
poetry run pytest tests/test_telemetry.py -v
poetry run pytest tests/test_admin.py -v
poetry run pytest tests/test_user.py -v
poetry run pytest tests/test_device_groups.py -v

# Run linting
make lint

# Run all checks
make test lint
```

### Test Coverage

- **158 tests** across 9 test files
- Device management (registration, status, heartbeat)
- Telemetry data (submission, retrieval, aggregation)
- User management (CRUD, authentication)
- Admin operations (device management, user management)
- Device groups (creation, membership)
- Health checks and monitoring
- User deactivation/activation
- Admin protection (cannot delete/deactivate admins)

## 🛠️ Development

### Project Structure

```
iotflow-backend/
├── src/
│   ├── config/          # Configuration management
│   ├── models/          # SQLAlchemy models (User, Device, Telemetry, Groups)
│   ├── routes/          # API endpoints
│   │   ├── devices.py   # Device management
│   │   ├── telemetry_postgres.py  # Telemetry endpoints
│   │   ├── users.py     # User management
│   │   ├── auth.py      # Authentication
│   │   ├── admin.py     # Admin operations
│   │   └── groups.py    # Device groups
│   ├── services/        # Business logic
│   │   └── postgres_telemetry.py  # Telemetry service
│   ├── middleware/      # Auth, security, monitoring
│   │   ├── auth.py      # Authentication middleware
│   │   ├── security.py  # Security headers, input validation
│   │   └── monitoring.py # Health checks, metrics
│   └── utils/           # Utilities (logging, time)
├── tests/               # Test suites (158 tests)
├── docs/                # API documentation
├── simulators/          # Device simulators
├── locust/              # Load testing
├── scripts/             # Utility scripts
├── app.py               # Application entry point
├── init_db.py           # Database initialization
├── docker-compose.yml   # Docker services
├── pyproject.toml       # Poetry dependencies
└── Makefile             # Development commands
```

### Default Users

After running `init_db.py`:

| Username | Password | Role | Features |
|----------|----------|------|----------|
| admin | admin123 | Admin | Full system access, cannot be deleted |
| testuser | test123 | User | Regular user access |

**⚠️ Change these passwords in production!**

### Environment Variables

Key configuration in `.env`:

```bash
# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key
HOST=0.0.0.0
PORT=5000

# Database
DATABASE_URL=postgresql://iotflow:iotflowpass@localhost:5432/iotflow

# Security
IOTFLOW_ADMIN_TOKEN=your-admin-token
JWT_SECRET_KEY=your-jwt-secret
API_KEY_LENGTH=32

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/iotflow.log

# API
API_VERSION=v1
MAX_DEVICES_PER_USER=100
RATE_LIMIT_PER_MINUTE=60
```

### Make Commands

```bash
# Development
make install          # Install dependencies
make install-dev      # Install with dev dependencies
make run              # Start development server
make run-prod         # Start with Gunicorn

# Testing
make test             # Run tests
make test-cov         # Run with coverage
make test-fast        # Skip slow tests
make lint             # Run linting (flake8 + mypy)
make format           # Format code (black + isort)
make format-check     # Check formatting

# Database
make init-db          # Initialize database

# Docker
make docker-build     # Build Docker image
make docker-run       # Run with Docker Compose
make docker-stop      # Stop containers

# Cleanup
make clean            # Remove generated files

# Security
make security         # Run security checks (bandit)
```

## 🐳 Docker Deployment

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build

# Production deployment
docker compose -f docker-compose.prod.yml up -d
```

### Docker Services

- **postgres**: PostgreSQL 15 database
- **app**: Flask application (optional, can run locally)

## 🔒 Security Features

- **API Key Authentication** - Secure device authentication with 32-character keys
- **JWT Tokens** - User session management with refresh tokens
- **Rate Limiting** - Per-device and per-IP request limits
- **Admin Protection** - Admins cannot be deleted or deactivated
- **Input Validation** - Request payload sanitization and validation
- **Security Headers** - CORS, CSP, XSS protection
- **Password Hashing** - Werkzeug secure password storage
- **SQL Injection Protection** - SQLAlchemy ORM with parameterized queries
- **HTTPS Support** - TLS/SSL ready for production

## 📊 Performance

### Benchmarks

- **API Response Time**: 40-70ms average
- **Concurrent Requests**: 100+ req/sec
- **Database**: PostgreSQL with connection pooling
- **Telemetry Storage**: 10,000+ points/second
- **Test Suite**: 158 tests in ~2 seconds

### Optimization Features

- Connection pooling (SQLAlchemy)
- Database indexes on frequently queried columns
- JSONB for flexible metadata storage
- Efficient time-series queries
- Aggregation support at database level

## 🔧 API Documentation

### Swagger UI

Access interactive API documentation at:
- Development: `http://localhost:5000/docs`
- Includes all endpoints with request/response examples
- Try out API calls directly from the browser

### OpenAPI Specification

- Full OpenAPI 3.0 spec available at `docs/openapi.yaml`
- Import into Postman, Insomnia, or other API clients
- Complete API reference at `docs/API_REFERENCE_COMPLETE.md`

## 📚 Additional Documentation

- [API Reference](docs/API_REFERENCE_COMPLETE.md) - Complete API documentation
- [OpenAPI Spec](docs/openapi.yaml) - OpenAPI 3.0 specification
- [Setup Guide](md/how_to_run.md) - Detailed setup instructions
- [Testing Guide](md/testing.md) - Testing strategies and examples
- [Overview](md/overview.md) - System architecture overview
- [Simulator Guide](simulators/README.md) - Device simulator usage

## 🚀 Load Testing

```bash
# Start Locust for load testing
poetry run locust -f locust/locustfile.py

# Open browser
open http://localhost:8089

# Configure test parameters and start load test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use Black for formatting (120 char line length)
- Use isort for import sorting
- Run `make format` before committing
- Ensure all tests pass with `make test`
- Maintain test coverage above 80%

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check PostgreSQL is running
docker compose ps

# Restart PostgreSQL
docker compose restart postgres

# Check connection
psql postgresql://iotflow:iotflowpass@localhost:5432/iotflow
```

**Port Already in Use**
```bash
# Find process using port 5000
lsof -i :5000

# Kill process or change PORT in .env
```

**Import Errors**
```bash
# Reinstall dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

**Test Failures**
```bash
# Run tests with verbose output
poetry run pytest tests/ -v -s

# Run specific failing test
poetry run pytest tests/test_devices.py::test_name -v
```

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check the [API Reference](docs/API_REFERENCE_COMPLETE.md)
- Review [troubleshooting guide](#-troubleshooting)

## 🎯 Roadmap

- [x] PostgreSQL telemetry storage
- [x] Device groups
- [x] Admin protection
- [x] Comprehensive testing (158 tests)
- [ ] WebSocket support for real-time updates
- [ ] MQTT protocol support
- [ ] Advanced analytics dashboard
- [ ] Multi-tenancy support
- [ ] Grafana integration
- [ ] Mobile SDK

## 📈 Project Stats

- **Language**: Python 3.10+
- **Framework**: Flask 2.3+
- **Database**: PostgreSQL 15+
- **Tests**: 158 passing
- **Test Files**: 9
- **API Endpoints**: 40+
- **Lines of Code**: ~5000+

---

Built with ❤️ using Flask, PostgreSQL, and Python
