// MongoDB Initialization Script for IoTFlow
// Creates collections with validation schemas and indexes

db = db.getSiblingDB('iotflow');

// Create device_configs collection with schema validation
db.createCollection('device_configs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['device_id', 'user_id', 'config_version'],
      properties: {
        device_id: {
          bsonType: 'int',
          description: 'Device ID - required'
        },
        user_id: {
          bsonType: 'int',
          description: 'User ID - required'
        },
        config_version: {
          bsonType: 'string',
          description: 'Configuration version - required'
        },
        settings: {
          bsonType: 'object',
          description: 'Device settings and configuration'
        },
        created_at: {
          bsonType: 'date'
        },
        updated_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

// Create indexes for device_configs
db.device_configs.createIndex({ device_id: 1 }, { unique: true });
db.device_configs.createIndex({ user_id: 1 });
db.device_configs.createIndex({ updated_at: -1 });

// Create event_logs collection
db.createCollection('event_logs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['event_type', 'timestamp'],
      properties: {
        event_type: {
          bsonType: 'string',
          description: 'Type of event'
        },
        device_id: {
          bsonType: 'int'
        },
        user_id: {
          bsonType: 'int'
        },
        timestamp: {
          bsonType: 'date'
        },
        details: {
          bsonType: 'object'
        },
        metadata: {
          bsonType: 'object'
        }
      }
    }
  }
});

// Create indexes for event_logs
db.event_logs.createIndex({ device_id: 1, timestamp: -1 });
db.event_logs.createIndex({ user_id: 1, timestamp: -1 });
db.event_logs.createIndex({ event_type: 1, timestamp: -1 });
db.event_logs.createIndex({ timestamp: -1 });

// Create alerts collection
db.createCollection('alerts', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['device_id', 'alert_type', 'severity', 'status'],
      properties: {
        device_id: {
          bsonType: 'int'
        },
        user_id: {
          bsonType: 'int'
        },
        alert_type: {
          bsonType: 'string',
          enum: ['threshold_exceeded', 'device_offline', 'anomaly', 'maintenance', 'custom']
        },
        severity: {
          bsonType: 'string',
          enum: ['info', 'warning', 'error', 'critical']
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'acknowledged', 'resolved']
        },
        message: {
          bsonType: 'string'
        },
        details: {
          bsonType: 'object'
        },
        acknowledged: {
          bsonType: 'bool'
        },
        created_at: {
          bsonType: 'date'
        },
        resolved_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

// Create indexes for alerts
db.alerts.createIndex({ device_id: 1, status: 1, created_at: -1 });
db.alerts.createIndex({ user_id: 1, status: 1, created_at: -1 });
db.alerts.createIndex({ severity: 1, status: 1 });
db.alerts.createIndex({ created_at: -1 });

// Create analytics collection
db.createCollection('analytics');
db.analytics.createIndex({ device_id: 1, report_type: 1, 'period.start': -1 });
db.analytics.createIndex({ user_id: 1, report_type: 1 });
db.analytics.createIndex({ generated_at: -1 });

// Create user_preferences collection
db.createCollection('user_preferences');
db.user_preferences.createIndex({ user_id: 1 }, { unique: true });
db.user_preferences.createIndex({ updated_at: -1 });

// Create device_metadata collection
db.createCollection('device_metadata');
db.device_metadata.createIndex({ device_id: 1 }, { unique: true });
db.device_metadata.createIndex({ tags: 1 });
db.device_metadata.createIndex({ 'location.coordinates': '2dsphere' });

print('IoTFlow MongoDB collections and indexes created successfully');
