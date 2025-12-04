"""
MongoDB Service
Handles flexible document storage for configs, events, alerts, and analytics
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson import ObjectId

logger = logging.getLogger(__name__)


class MongoDBService:
    """Service for managing document data in MongoDB"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        self.uri = os.getenv('MONGODB_URI', 'mongodb://iotflow:iotflowpass@localhost:27017/iotflow?authSource=admin')
        self.database_name = os.getenv('MONGODB_DATABASE', 'iotflow')
        
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            
            # Ensure indexes
            self._ensure_indexes()
            
            logger.info(f"Connected to MongoDB database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
    
    def _ensure_indexes(self):
        """Ensure indexes exist"""
        try:
            # Device configs indexes
            self.db.device_configs.create_index([("device_id", ASCENDING)], unique=True)
            self.db.device_configs.create_index([("user_id", ASCENDING)])
            
            # Event logs indexes
            self.db.event_logs.create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])
            self.db.event_logs.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
            self.db.event_logs.create_index([("event_type", ASCENDING)])
            
            # Alerts indexes
            self.db.alerts.create_index([("device_id", ASCENDING), ("status", ASCENDING)])
            self.db.alerts.create_index([("severity", ASCENDING)])
            
            # User preferences indexes
            self.db.user_preferences.create_index([("user_id", ASCENDING)], unique=True)
            
            # Device metadata indexes
            self.db.device_metadata.create_index([("device_id", ASCENDING)], unique=True)
            self.db.device_metadata.create_index([("tags", ASCENDING)])
            
            logger.info("MongoDB indexes ensured")
        except Exception as e:
            logger.error(f"Error ensuring indexes: {e}")
    
    def is_available(self) -> bool:
        """Check if MongoDB is available"""
        if not self.client:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB not available: {e}")
            return False
    
    # Device Configurations
    
    def create_device_config(self, config: Dict) -> Optional[Dict]:
        """Create device configuration"""
        try:
            config['created_at'] = datetime.now(timezone.utc)
            config['updated_at'] = datetime.now(timezone.utc)
            
            result = self.db.device_configs.insert_one(config)
            return {'config_id': str(result.inserted_id)}
        except DuplicateKeyError:
            logger.error(f"Device config already exists for device_id: {config.get('device_id')}")
            return None
        except Exception as e:
            logger.error(f"Error creating device config: {e}")
            return None
    
    def get_device_config(self, device_id: int) -> Optional[Dict]:
        """Get device configuration"""
        try:
            config = self.db.device_configs.find_one({"device_id": device_id})
            if config:
                config['_id'] = str(config['_id'])
            return config
        except Exception as e:
            logger.error(f"Error getting device config: {e}")
            return None
    
    def update_device_config(self, device_id: int, updates: Dict) -> bool:
        """Update device configuration"""
        try:
            updates['updated_at'] = datetime.now(timezone.utc)
            result = self.db.device_configs.update_one(
                {"device_id": device_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating device config: {e}")
            return False
    
    def delete_device_config(self, device_id: int) -> bool:
        """Delete device configuration"""
        try:
            result = self.db.device_configs.delete_one({"device_id": device_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting device config: {e}")
            return False
    
    def get_user_configs(self, user_id: int) -> List[Dict]:
        """Get all configs for a user"""
        try:
            configs = list(self.db.device_configs.find({"user_id": user_id}))
            for config in configs:
                config['_id'] = str(config['_id'])
            return configs
        except Exception as e:
            logger.error(f"Error getting user configs: {e}")
            return []
    
    # Event Logging
    
    def log_event(self, event: Dict) -> Optional[Dict]:
        """Log an event"""
        try:
            event['timestamp'] = event.get('timestamp', datetime.now(timezone.utc))
            
            result = self.db.event_logs.insert_one(event)
            return {'event_id': str(result.inserted_id)}
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return None
    
    def get_device_events(self, device_id: int, limit: int = 100) -> List[Dict]:
        """Get device events"""
        try:
            events = list(self.db.event_logs.find(
                {"device_id": device_id}
            ).sort("timestamp", DESCENDING).limit(limit))
            
            for event in events:
                event['_id'] = str(event['_id'])
            return events
        except Exception as e:
            logger.error(f"Error getting device events: {e}")
            return []
    
    def get_user_events(self, user_id: int, limit: int = 100) -> List[Dict]:
        """Get user events"""
        try:
            events = list(self.db.event_logs.find(
                {"user_id": user_id}
            ).sort("timestamp", DESCENDING).limit(limit))
            
            for event in events:
                event['_id'] = str(event['_id'])
            return events
        except Exception as e:
            logger.error(f"Error getting user events: {e}")
            return []
    
    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        """Get events by type"""
        try:
            events = list(self.db.event_logs.find(
                {"event_type": event_type}
            ).sort("timestamp", DESCENDING).limit(limit))
            
            for event in events:
                event['_id'] = str(event['_id'])
            return events
        except Exception as e:
            logger.error(f"Error getting events by type: {e}")
            return []
    
    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get events within time range"""
        try:
            query = {}
            if start_time or end_time:
                query['timestamp'] = {}
                if start_time:
                    query['timestamp']['$gte'] = start_time
                if end_time:
                    query['timestamp']['$lte'] = end_time
            
            events = list(self.db.event_logs.find(query).sort("timestamp", DESCENDING).limit(limit))
            
            for event in events:
                event['_id'] = str(event['_id'])
            return events
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
    
    # Alert Management
    
    def create_alert(self, alert: Dict) -> Optional[Dict]:
        """Create an alert"""
        try:
            alert['created_at'] = datetime.now(timezone.utc)
            alert['acknowledged'] = alert.get('acknowledged', False)
            
            result = self.db.alerts.insert_one(alert)
            return {'alert_id': str(result.inserted_id)}
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None
    
    def get_alert(self, alert_id: str) -> Optional[Dict]:
        """Get alert by ID"""
        try:
            if not ObjectId.is_valid(alert_id):
                return None
            
            alert = self.db.alerts.find_one({"_id": ObjectId(alert_id)})
            if alert:
                alert['_id'] = str(alert['_id'])
            return alert
        except Exception as e:
            logger.error(f"Error getting alert: {e}")
            return None
    
    def get_device_alerts(self, device_id: int, limit: int = 100) -> List[Dict]:
        """Get device alerts"""
        try:
            alerts = list(self.db.alerts.find(
                {"device_id": device_id}
            ).sort("created_at", DESCENDING).limit(limit))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            return alerts
        except Exception as e:
            logger.error(f"Error getting device alerts: {e}")
            return []
    
    def get_active_alerts(self, limit: int = 100) -> List[Dict]:
        """Get active alerts"""
        try:
            alerts = list(self.db.alerts.find(
                {"status": "active"}
            ).sort("created_at", DESCENDING).limit(limit))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            return alerts
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            if not ObjectId.is_valid(alert_id):
                return False
            
            result = self.db.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"acknowledged": True, "acknowledged_at": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            if not ObjectId.is_valid(alert_id):
                return False
            
            result = self.db.alerts.update_one(
                {"_id": ObjectId(alert_id)},
                {"$set": {"status": "resolved", "resolved_at": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_alerts_by_severity(self, severity: str, limit: int = 100) -> List[Dict]:
        """Get alerts by severity"""
        try:
            alerts = list(self.db.alerts.find(
                {"severity": severity}
            ).sort("created_at", DESCENDING).limit(limit))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts by severity: {e}")
            return []
    
    # Analytics
    
    def create_analytics_report(self, report: Dict) -> Optional[Dict]:
        """Create analytics report"""
        try:
            report['generated_at'] = datetime.now(timezone.utc)
            
            result = self.db.analytics.insert_one(report)
            return {'report_id': str(result.inserted_id)}
        except Exception as e:
            logger.error(f"Error creating analytics report: {e}")
            return None
    
    def get_device_reports(self, device_id: int, limit: int = 10) -> List[Dict]:
        """Get device reports"""
        try:
            reports = list(self.db.analytics.find(
                {"device_id": device_id}
            ).sort("generated_at", DESCENDING).limit(limit))
            
            for report in reports:
                report['_id'] = str(report['_id'])
            return reports
        except Exception as e:
            logger.error(f"Error getting device reports: {e}")
            return []
    
    def get_latest_report(self, device_id: int, report_type: str) -> Optional[Dict]:
        """Get latest report for device"""
        try:
            report = self.db.analytics.find_one(
                {"device_id": device_id, "report_type": report_type},
                sort=[("generated_at", DESCENDING)]
            )
            if report:
                report['_id'] = str(report['_id'])
            return report
        except Exception as e:
            logger.error(f"Error getting latest report: {e}")
            return None
    
    # User Preferences
    
    def create_user_preferences(self, preferences: Dict) -> Optional[Dict]:
        """Create user preferences"""
        try:
            preferences['created_at'] = datetime.now(timezone.utc)
            preferences['updated_at'] = datetime.now(timezone.utc)
            
            result = self.db.user_preferences.insert_one(preferences)
            return {'preferences_id': str(result.inserted_id)}
        except DuplicateKeyError:
            logger.error(f"User preferences already exist for user_id: {preferences.get('user_id')}")
            return None
        except Exception as e:
            logger.error(f"Error creating user preferences: {e}")
            return None
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        try:
            prefs = self.db.user_preferences.find_one({"user_id": user_id})
            if prefs:
                prefs['_id'] = str(prefs['_id'])
            return prefs
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    def update_user_preferences(self, user_id: int, updates: Dict) -> bool:
        """Update user preferences"""
        try:
            updates['updated_at'] = datetime.now(timezone.utc)
            result = self.db.user_preferences.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return False
    
    # Device Metadata
    
    def create_device_metadata(self, metadata: Dict) -> Optional[Dict]:
        """Create device metadata"""
        try:
            metadata['created_at'] = datetime.now(timezone.utc)
            metadata['updated_at'] = datetime.now(timezone.utc)
            
            result = self.db.device_metadata.insert_one(metadata)
            return {'metadata_id': str(result.inserted_id)}
        except DuplicateKeyError:
            logger.error(f"Device metadata already exists for device_id: {metadata.get('device_id')}")
            return None
        except Exception as e:
            logger.error(f"Error creating device metadata: {e}")
            return None
    
    def get_device_metadata(self, device_id: int) -> Optional[Dict]:
        """Get device metadata"""
        try:
            metadata = self.db.device_metadata.find_one({"device_id": device_id})
            if metadata:
                metadata['_id'] = str(metadata['_id'])
            return metadata
        except Exception as e:
            logger.error(f"Error getting device metadata: {e}")
            return None
    
    def add_device_tag(self, device_id: int, tag: str) -> bool:
        """Add tag to device"""
        try:
            result = self.db.device_metadata.update_one(
                {"device_id": device_id},
                {"$addToSet": {"tags": tag}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding device tag: {e}")
            return False
    
    def remove_device_tag(self, device_id: int, tag: str) -> bool:
        """Remove tag from device"""
        try:
            result = self.db.device_metadata.update_one(
                {"device_id": device_id},
                {"$pull": {"tags": tag}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing device tag: {e}")
            return False
    
    def find_devices_by_tag(self, tag: str) -> List[Dict]:
        """Find devices by tag"""
        try:
            devices = list(self.db.device_metadata.find({"tags": tag}))
            for device in devices:
                device['_id'] = str(device['_id'])
            return devices
        except Exception as e:
            logger.error(f"Error finding devices by tag: {e}")
            return []
    
    def find_devices_near(
        self,
        longitude: float,
        latitude: float,
        max_distance: int = 1000
    ) -> List[Dict]:
        """Find devices near coordinates"""
        try:
            devices = list(self.db.device_metadata.find({
                "location": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [longitude, latitude]
                        },
                        "$maxDistance": max_distance
                    }
                }
            }))
            for device in devices:
                device['_id'] = str(device['_id'])
            return devices
        except Exception as e:
            logger.error(f"Error finding devices near location: {e}")
            return []
    
    # Aggregation Pipelines
    
    def aggregate_alerts_by_severity(self) -> List[Dict]:
        """Aggregate alerts by severity"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$severity",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            return list(self.db.alerts.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error aggregating alerts by severity: {e}")
            return []
    
    def aggregate_events_by_type(self) -> List[Dict]:
        """Aggregate events by type"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            return list(self.db.event_logs.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error aggregating events by type: {e}")
            return []
    
    # Bulk Operations
    
    def bulk_insert_events(self, events: List[Dict]) -> bool:
        """Bulk insert events"""
        try:
            for event in events:
                event['timestamp'] = event.get('timestamp', datetime.now(timezone.utc))
            
            self.db.event_logs.insert_many(events)
            return True
        except Exception as e:
            logger.error(f"Error bulk inserting events: {e}")
            return False
    
    def bulk_update_configs(self, filter: Dict, updates: Dict) -> bool:
        """Bulk update configs"""
        try:
            updates['updated_at'] = datetime.now(timezone.utc)
            result = self.db.device_configs.update_many(filter, {"$set": updates})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error bulk updating configs: {e}")
            return False
    
    # Index Management
    
    def create_indexes(self) -> bool:
        """Create indexes"""
        try:
            self._ensure_indexes()
            return True
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
    
    def list_indexes(self, collection_name: str) -> List[Dict]:
        """List collection indexes"""
        try:
            collection = self.db[collection_name]
            return list(collection.list_indexes())
        except Exception as e:
            logger.error(f"Error listing indexes: {e}")
            return []
    
    # Error Handling
    
    def handle_connection_error(self):
        """Handle connection errors"""
        logger.error("MongoDB connection error")
        self._connect()
    
    # Test Utilities
    
    def cleanup_test_data(self):
        """Cleanup test data"""
        try:
            self.db.device_configs.delete_many({})
            self.db.event_logs.delete_many({})
            self.db.alerts.delete_many({})
            self.db.analytics.delete_many({})
            self.db.user_preferences.delete_many({})
            self.db.device_metadata.delete_many({})
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
    
    def close(self):
        """Close connection"""
        if self.client:
            self.client.close()
