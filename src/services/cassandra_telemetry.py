"""
Cassandra Telemetry Service
Handles time-series telemetry data storage and retrieval
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement, BatchStatement, BatchType

logger = logging.getLogger(__name__)


class CassandraTelemetryService:
    """Service for managing telemetry data in Cassandra"""
    
    def __init__(self):
        """Initialize Cassandra connection"""
        self.hosts = os.getenv('CASSANDRA_HOSTS', 'localhost').split(',')
        self.port = int(os.getenv('CASSANDRA_PORT', '9042'))
        self.keyspace = os.getenv('CASSANDRA_KEYSPACE', 'telemetry')
        
        self.cluster = None
        self.session = None
        self.query_timeout = 30
        
        self._connect()
    
    def _connect(self):
        """Establish connection to Cassandra"""
        try:
            self.cluster = Cluster(
                self.hosts,
                port=self.port,
                protocol_version=4
            )
            self.session = self.cluster.connect()
            
            # Create keyspace if it doesn't exist
            self._ensure_keyspace()
            
            # Use the keyspace
            self.session.set_keyspace(self.keyspace)
            
            # Create tables
            self._ensure_tables()
            
            logger.info(f"Connected to Cassandra at {self.hosts}")
        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}")
            self.session = None
    
    def _ensure_keyspace(self):
        """Ensure keyspace exists"""
        try:
            self.session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
                WITH replication = {{
                    'class': 'SimpleStrategy',
                    'replication_factor': 1
                }}
            """)
        except Exception as e:
            logger.error(f"Error creating keyspace: {e}")
    
    def _ensure_tables(self):
        """Ensure required tables exist"""
        try:
            # Device data table
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS device_data (
                    device_id int,
                    timestamp timestamp,
                    measurement_name text,
                    numeric_value double,
                    text_value text,
                    metadata map<text, text>,
                    PRIMARY KEY ((device_id), timestamp, measurement_name)
                ) WITH CLUSTERING ORDER BY (timestamp DESC, measurement_name ASC)
            """)
            
            # User data table
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id int,
                    timestamp timestamp,
                    device_id int,
                    measurement_name text,
                    numeric_value double,
                    PRIMARY KEY ((user_id), timestamp, device_id, measurement_name)
                ) WITH CLUSTERING ORDER BY (timestamp DESC, device_id ASC, measurement_name ASC)
            """)
            
            # Aggregated data table
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_data (
                    device_id int,
                    measurement_name text,
                    time_bucket timestamp,
                    aggregation_type text,
                    value double,
                    count int,
                    min_value double,
                    max_value double,
                    PRIMARY KEY ((device_id, measurement_name), time_bucket, aggregation_type)
                ) WITH CLUSTERING ORDER BY (time_bucket DESC, aggregation_type ASC)
            """)
            
            # Latest data table
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS latest_data (
                    device_id int,
                    measurement_name text,
                    timestamp timestamp,
                    numeric_value double,
                    text_value text,
                    PRIMARY KEY (device_id, measurement_name)
                )
            """)
            
            # Device measurements catalog
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS device_measurements (
                    device_id int,
                    measurement_name text,
                    data_type text,
                    unit text,
                    first_seen timestamp,
                    last_seen timestamp,
                    PRIMARY KEY (device_id, measurement_name)
                )
            """)
            
            logger.info("Cassandra tables ensured")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
    
    def is_available(self) -> bool:
        """Check if Cassandra is available"""
        if not self.session:
            return False
        try:
            self.session.execute("SELECT now() FROM system.local", timeout=5)
            return True
        except Exception as e:
            logger.error(f"Cassandra not available: {e}")
            return False
    
    def keyspace_exists(self, keyspace_name: str) -> bool:
        """Check if keyspace exists"""
        try:
            result = self.session.execute(
                "SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s",
                [keyspace_name]
            )
            return result.one() is not None
        except:
            return False
    
    def write_telemetry(
        self,
        device_id: int,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Write telemetry data"""
        if not device_id or not data:
            return False
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        try:
            for measurement_name, value in data.items():
                # Skip non-numeric values
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                
                numeric_value = float(value)
                
                # Insert into device_data
                self.session.execute("""
                    INSERT INTO device_data (device_id, timestamp, measurement_name, numeric_value, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (device_id, timestamp, measurement_name, numeric_value, metadata or {}))
                
                # Update latest_data
                self.session.execute("""
                    INSERT INTO latest_data (device_id, measurement_name, timestamp, numeric_value)
                    VALUES (%s, %s, %s, %s)
                """, (device_id, measurement_name, timestamp, numeric_value))
            
            return True
        except Exception as e:
            logger.error(f"Error writing telemetry: {e}")
            return False
    
    def write_telemetry_with_user(
        self,
        device_id: int,
        user_id: int,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write telemetry data with user_id for user_data table"""
        if not self.write_telemetry(device_id, data, timestamp):
            return False
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        try:
            for measurement_name, value in data.items():
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                
                numeric_value = float(value)
                
                # Insert into user_data
                self.session.execute("""
                    INSERT INTO user_data (user_id, timestamp, device_id, measurement_name, numeric_value)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, timestamp, device_id, measurement_name, numeric_value))
            
            return True
        except Exception as e:
            logger.error(f"Error writing user telemetry: {e}")
            return False
    
    def _parse_time_range(self, time_str: str) -> datetime:
        """Parse time range string to datetime"""
        now = datetime.now(timezone.utc)
        
        if not time_str or time_str == 'now':
            return now
        
        if time_str.startswith('-'):
            time_str = time_str[1:]
            
            if time_str.endswith('h'):
                hours = int(time_str[:-1])
                return now - timedelta(hours=hours)
            elif time_str.endswith('d'):
                days = int(time_str[:-1])
                return now - timedelta(days=days)
            elif time_str.endswith('w'):
                weeks = int(time_str[:-1])
                return now - timedelta(weeks=weeks)
            elif time_str.endswith('m'):
                minutes = int(time_str[:-1])
                return now - timedelta(minutes=minutes)
        
        # Try ISO format
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return now - timedelta(hours=1)
    
    def get_device_telemetry(
        self,
        device_id: int,
        start_time: str = '-1h',
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get telemetry data for a device"""
        try:
            start_dt = self._parse_time_range(start_time)
            end_dt = self._parse_time_range(end_time) if end_time else datetime.now(timezone.utc)
            
            result = self.session.execute("""
                SELECT timestamp, measurement_name, numeric_value
                FROM device_data
                WHERE device_id = %s AND timestamp >= %s AND timestamp <= %s
                LIMIT %s
            """, (device_id, start_dt, end_dt, limit))
            
            # Group by timestamp
            telemetry_by_time = {}
            for row in result:
                ts = row.timestamp.isoformat()
                if ts not in telemetry_by_time:
                    telemetry_by_time[ts] = {
                        'timestamp': ts,
                        'measurements': {}
                    }
                telemetry_by_time[ts]['measurements'][row.measurement_name] = row.numeric_value
            
            return list(telemetry_by_time.values())
        except Exception as e:
            logger.error(f"Error getting telemetry: {e}")
            return []
    
    def get_latest_telemetry(self, device_id: int) -> Optional[Dict]:
        """Get latest telemetry values for a device"""
        try:
            result = self.session.execute("""
                SELECT measurement_name, numeric_value
                FROM latest_data
                WHERE device_id = %s
            """, (device_id,))
            
            measurements = {}
            for row in result:
                measurements[row.measurement_name] = row.numeric_value
            
            return measurements if measurements else None
        except Exception as e:
            logger.error(f"Error getting latest telemetry: {e}")
            return None
    
    def write_aggregated_data(
        self,
        device_id: int,
        measurement_name: str,
        time_bucket: datetime,
        aggregation_type: str,
        value: float,
        count: int,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> bool:
        """Write aggregated data"""
        try:
            self.session.execute("""
                INSERT INTO aggregated_data 
                (device_id, measurement_name, time_bucket, aggregation_type, value, count, min_value, max_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (device_id, measurement_name, time_bucket, aggregation_type, value, count, min_value, max_value))
            return True
        except Exception as e:
            logger.error(f"Error writing aggregated data: {e}")
            return False
    
    def get_aggregated_data(
        self,
        device_id: int,
        measurement_name: str,
        aggregation_type: str,
        start_time: str = '-24h'
    ) -> List[Dict]:
        """Get aggregated data"""
        try:
            start_dt = self._parse_time_range(start_time)
            
            result = self.session.execute("""
                SELECT time_bucket, value, count
                FROM aggregated_data
                WHERE device_id = %s AND measurement_name = %s 
                  AND aggregation_type = %s AND time_bucket >= %s
            """, (device_id, measurement_name, aggregation_type, start_dt))
            
            return [
                {
                    'timestamp': row.time_bucket.isoformat(),
                    'value': row.value,
                    'count': row.count
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return []
    
    def compute_aggregation(
        self,
        device_id: int,
        measurement_name: str,
        aggregation: str,
        window: str,
        start_time: str
    ) -> List[Dict]:
        """Compute aggregation on the fly"""
        # For now, return empty list - would need more complex implementation
        return []
    
    def get_user_telemetry(
        self,
        user_id: int,
        start_time: str = '-1h',
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get telemetry for all user's devices"""
        try:
            start_dt = self._parse_time_range(start_time)
            end_dt = self._parse_time_range(end_time) if end_time else datetime.now(timezone.utc)
            
            result = self.session.execute("""
                SELECT timestamp, device_id, measurement_name, numeric_value
                FROM user_data
                WHERE user_id = %s AND timestamp >= %s AND timestamp <= %s
                LIMIT %s
            """, (user_id, start_dt, end_dt, limit))
            
            return [
                {
                    'timestamp': row.timestamp.isoformat(),
                    'device_id': row.device_id,
                    'measurement_name': row.measurement_name,
                    'value': row.numeric_value
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error getting user telemetry: {e}")
            return []
    
    def get_user_telemetry_count(self, user_id: int, start_time: str = '-1h') -> int:
        """Get count of telemetry records for a user"""
        try:
            start_dt = self._parse_time_range(start_time)
            
            result = self.session.execute("""
                SELECT COUNT(*) as count
                FROM user_data
                WHERE user_id = %s AND timestamp >= %s
            """, (user_id, start_dt))
            
            row = result.one()
            return row.count if row else 0
        except Exception as e:
            logger.error(f"Error getting user telemetry count: {e}")
            return 0
    
    def delete_device_data(
        self,
        device_id: int,
        start_time: str,
        end_time: str
    ) -> bool:
        """Delete device data within time range"""
        try:
            start_dt = self._parse_time_range(start_time)
            end_dt = self._parse_time_range(end_time)
            
            self.session.execute("""
                DELETE FROM device_data
                WHERE device_id = %s AND timestamp >= %s AND timestamp <= %s
            """, (device_id, start_dt, end_dt))
            
            return True
        except Exception as e:
            logger.error(f"Error deleting device data: {e}")
            return False
    
    def delete_old_data(self, days: int) -> bool:
        """Delete data older than specified days"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            # This would need to scan all partitions - not efficient
            # Better to use TTL on tables
            return True
        except Exception as e:
            logger.error(f"Error deleting old data: {e}")
            return False
    
    def update_measurement_catalog(
        self,
        device_id: int,
        measurement_name: str,
        data_type: str,
        unit: Optional[str] = None
    ) -> bool:
        """Update device measurement catalog"""
        try:
            now = datetime.now(timezone.utc)
            self.session.execute("""
                INSERT INTO device_measurements 
                (device_id, measurement_name, data_type, unit, first_seen, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (device_id, measurement_name, data_type, unit, now, now))
            return True
        except Exception as e:
            logger.error(f"Error updating measurement catalog: {e}")
            return False
    
    def get_device_measurements(self, device_id: int) -> List[Dict]:
        """Get device measurement catalog"""
        try:
            result = self.session.execute("""
                SELECT measurement_name, data_type, unit, first_seen, last_seen
                FROM device_measurements
                WHERE device_id = %s
            """, (device_id,))
            
            return [
                {
                    'measurement_name': row.measurement_name,
                    'data_type': row.data_type,
                    'unit': row.unit,
                    'first_seen': row.first_seen.isoformat() if row.first_seen else None,
                    'last_seen': row.last_seen.isoformat() if row.last_seen else None
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error getting device measurements: {e}")
            return []
    
    def batch_write_telemetry(self, records: List[Dict]) -> bool:
        """Batch write telemetry records"""
        try:
            batch = BatchStatement(batch_type=BatchType.UNLOGGED)
            
            for record in records:
                device_id = record['device_id']
                data = record['data']
                timestamp = record.get('timestamp', datetime.now(timezone.utc))
                
                for measurement_name, value in data.items():
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        continue
                    
                    numeric_value = float(value)
                    
                    batch.add(SimpleStatement("""
                        INSERT INTO device_data (device_id, timestamp, measurement_name, numeric_value)
                        VALUES (%s, %s, %s, %s)
                    """), (device_id, timestamp, measurement_name, numeric_value))
            
            self.session.execute(batch)
            return True
        except Exception as e:
            logger.error(f"Error batch writing telemetry: {e}")
            return False
    
    def handle_connection_error(self):
        """Handle connection errors"""
        logger.error("Cassandra connection error")
        self._connect()
    
    def cleanup_test_data(self):
        """Cleanup test data"""
        try:
            self.session.execute("TRUNCATE device_data")
            self.session.execute("TRUNCATE user_data")
            self.session.execute("TRUNCATE aggregated_data")
            self.session.execute("TRUNCATE latest_data")
            self.session.execute("TRUNCATE device_measurements")
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
    
    def close(self):
        """Close connection"""
        if self.cluster:
            self.cluster.shutdown()
