-- Cassandra Initialization Script for IoTFlow
-- Creates keyspace and tables for time-series telemetry data

-- Create keyspace with SimpleStrategy (for single datacenter)
-- For production multi-datacenter, use NetworkTopologyStrategy
CREATE KEYSPACE IF NOT EXISTS telemetry
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE telemetry;

-- Table 1: Device telemetry data (primary query pattern: by device and time)
CREATE TABLE IF NOT EXISTS device_data (
    device_id int,
    timestamp timestamp,
    measurement_name text,
    numeric_value double,
    text_value text,
    metadata map<text, text>,
    PRIMARY KEY ((device_id), timestamp, measurement_name)
) WITH CLUSTERING ORDER BY (timestamp DESC, measurement_name ASC)
AND compaction = {'class': 'TimeWindowCompactionStrategy', 'compaction_window_size': 1, 'compaction_window_unit': 'DAYS'}
AND default_time_to_live = 7776000  -- 90 days retention
AND comment = 'Time-series telemetry data partitioned by device';

-- Table 2: User telemetry data (query pattern: all devices for a user)
CREATE TABLE IF NOT EXISTS user_data (
    user_id int,
    timestamp timestamp,
    device_id int,
    measurement_name text,
    numeric_value double,
    PRIMARY KEY ((user_id), timestamp, device_id, measurement_name)
) WITH CLUSTERING ORDER BY (timestamp DESC, device_id ASC, measurement_name ASC)
AND compaction = {'class': 'TimeWindowCompactionStrategy', 'compaction_window_size': 1, 'compaction_window_unit': 'DAYS'}
AND default_time_to_live = 7776000  -- 90 days retention
AND comment = 'User-centric view of telemetry data';

-- Table 3: Aggregated data (hourly/daily rollups)
CREATE TABLE IF NOT EXISTS aggregated_data (
    device_id int,
    measurement_name text,
    time_bucket timestamp,
    aggregation_type text,  -- 'hourly', 'daily', 'weekly'
    value double,
    count int,
    min_value double,
    max_value double,
    PRIMARY KEY ((device_id, measurement_name), time_bucket, aggregation_type)
) WITH CLUSTERING ORDER BY (time_bucket DESC, aggregation_type ASC)
AND compaction = {'class': 'TimeWindowCompactionStrategy', 'compaction_window_size': 7, 'compaction_window_unit': 'DAYS'}
AND default_time_to_live = 31536000  -- 365 days retention for aggregated data
AND comment = 'Pre-aggregated telemetry data for faster queries';

-- Table 4: Latest telemetry values (for quick access to current state)
CREATE TABLE IF NOT EXISTS latest_data (
    device_id int,
    measurement_name text,
    timestamp timestamp,
    numeric_value double,
    text_value text,
    PRIMARY KEY (device_id, measurement_name)
) WITH comment = 'Latest value for each measurement per device';

-- Table 5: Device measurement catalog (track what measurements each device reports)
CREATE TABLE IF NOT EXISTS device_measurements (
    device_id int,
    measurement_name text,
    data_type text,  -- 'numeric', 'text', 'boolean'
    unit text,
    first_seen timestamp,
    last_seen timestamp,
    sample_count counter,
    PRIMARY KEY (device_id, measurement_name)
) WITH comment = 'Catalog of measurements reported by each device';

-- Create secondary indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_device_data_measurement ON device_data (measurement_name);
CREATE INDEX IF NOT EXISTS idx_user_data_device ON user_data (device_id);

-- Materialized view for recent data (last 24 hours)
-- Note: Materialized views have limitations, consider using application-level caching instead
-- CREATE MATERIALIZED VIEW IF NOT EXISTS recent_device_data AS
--     SELECT device_id, timestamp, measurement_name, numeric_value
--     FROM device_data
--     WHERE device_id IS NOT NULL 
--       AND timestamp IS NOT NULL 
--       AND measurement_name IS NOT NULL
--     PRIMARY KEY ((device_id), timestamp, measurement_name)
--     WITH CLUSTERING ORDER BY (timestamp DESC);

-- Grant permissions (if using authentication)
-- GRANT SELECT, MODIFY ON KEYSPACE telemetry TO iotflow_user;
