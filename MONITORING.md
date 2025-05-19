# Image Transformation Bot Monitoring

This document describes the monitoring setup for the Image Transformation Bot, which uses Prometheus for metrics collection and Grafana for visualization.

## Overview

The monitoring stack includes:
- Prometheus for metrics collection
- Grafana for visualization
- Custom metrics for image processing, API calls, and vendor activity
- Structured logging with correlation IDs

## Prerequisites

- Docker and Docker Compose installed
- Ports 3000 (Grafana) and 9090 (Prometheus) available
- The Image Transformation Bot running on port 8000

## Quick Start

1. Create the required directories:
```bash
mkdir -p prometheus grafana/dashboards
```

2. Start the monitoring stack:
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

3. Access the dashboards:
   - Grafana: http://localhost:3000 (default credentials: admin/admin)
   - Prometheus: http://localhost:9090

4. Configure Grafana:
   - Add Prometheus as a data source:
     - Go to Configuration > Data Sources
     - Click "Add data source"
     - Select "Prometheus"
     - Set URL to: http://prometheus:9090
     - Click "Save & Test"

5. Import the dashboard:
   - Go to Dashboards > Import
   - Upload the `grafana/dashboards/image-transformation.json` file
   - Select the Prometheus data source
   - Click "Import"

## Available Metrics

### Request Metrics
- `vendor_requests_total`: Total requests per vendor
- `error_total`: Error counts by type and vendor

### Performance Metrics
- `image_processing_duration_seconds`: Time spent processing images
- `image_size_bytes`: Size of processed images
- `s3_operation_duration_seconds`: S3 operation durations
- `stability_api_duration_seconds`: Stability API call durations

### Dashboard Panels

1. **Request Rate by Vendor**
   - Shows the rate of requests per vendor
   - Helps identify high-volume vendors
   - Monitors overall system load

2. **Image Processing Duration**
   - Tracks processing time for different operations
   - Helps identify performance bottlenecks
   - Monitors system efficiency

3. **Error Rate**
   - Displays error rates by type and vendor
   - Helps identify problematic operations
   - Monitors system stability

4. **Average Image Size**
   - Shows average size of processed images
   - Helps track resource usage
   - Monitors storage requirements

## Logging

The system uses structured JSON logging with the following features:
- Correlation IDs for request tracing
- Vendor ID tracking
- Detailed error logging
- Performance metrics
- Operation timestamps

### Log Format Example
```json
{
  "timestamp": "2024-03-21T10:00:00Z",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "vendor_id": "user_1",
  "message": "Request completed",
  "processing_time": 2.5,
  "s3_url": "https://..."
}
```

## Data Retention

- Prometheus data is retained for 7 days
- Logs are streamed to stdout (can be collected by your logging system)

## Alerting

The system tracks various metrics that can be used for alerting:
- High error rates
- Slow processing times
- Failed API calls
- S3 operation failures

To set up alerts:
1. Go to Grafana > Alerting
2. Create new alert rules based on the metrics
3. Configure notification channels (email, Slack, etc.)

## Troubleshooting

1. **Prometheus not collecting metrics**
   - Check if the Image Transformation Bot is running
   - Verify the metrics endpoint is accessible
   - Check Prometheus logs: `docker logs prometheus`

2. **Grafana not showing data**
   - Verify Prometheus data source is configured correctly
   - Check if metrics are being collected in Prometheus
   - Verify time range in dashboard

3. **High error rates**
   - Check application logs for detailed error messages
   - Verify external service (Stability API) status
   - Check S3 connectivity

## Security Considerations

- Grafana admin password is set to 'admin' by default - change it in production
- Prometheus and Grafana are exposed on localhost only
- Consider setting up authentication for production use
- Use HTTPS in production environments

## Maintenance

1. **Updating the stack**
```bash
docker-compose -f docker-compose.monitoring.yml pull
docker-compose -f docker-compose.monitoring.yml up -d
```

2. **Backing up data**
- Grafana dashboards are stored in `grafana/dashboards/`
- Prometheus data is stored in a Docker volume
- Export important dashboards as JSON files

3. **Cleaning up**
```bash
docker-compose -f docker-compose.monitoring.yml down
```

## Contributing

To add new metrics:
1. Add the metric in `app/metrics.py`
2. Update the API code to use the metric
3. Add a new panel to the Grafana dashboard

## Support

For issues or questions:
1. Check the application logs
2. Review Prometheus metrics
3. Check Grafana dashboard for anomalies
4. Contact the development team

## Database Logging Table for Monitoring

A new table, `MonitoringLog`, is provided for structured logging of monitoring events. This table combines API monitoring capabilities with flexible logging features, designed to be added to your Saleor database and referenced from any Saleor table using the `user_id`, `correlation_id`, or `vendor_id` fields.

### Table Schema (MonitoringLog.sql)
```sql
CREATE TABLE `MonitoringLog` (
  `id` SERIAL PRIMARY KEY,
  `user_id` UUID,                                -- User's UUID in system
  `vendor_id` varchar(64),                       -- Vendor identifier
  `endpoint` TEXT NOT NULL,                      -- Which API endpoint was called
  `request_id` TEXT UNIQUE NOT NULL,             -- Service-generated request UUID
  `correlation_id` varchar(64),                  -- For cross-referencing with other systems
  `level` varchar(16) NOT NULL,                  -- Log level (INFO, ERROR, etc.)
  `message` text,                                -- Log message
  `latency_ms` INTEGER NOT NULL,                 -- Processing time in milliseconds
  `status_code` INTEGER NOT NULL,                -- HTTP response code
  `s3_url` varchar(512),                         -- S3 URL if applicable
  `extra_data` jsonb,                            -- Additional structured data
  `created_at` TIMESTAMPTZ NOT NULL DEFAULT now() -- Log insertion timestamp
);
```

### Key Features
- **API Monitoring**: Tracks endpoints, status codes, and latency
- **User Tracking**: Uses UUID for user identification
- **Request Tracing**: Unique request IDs prevent duplicate logging
- **Flexible Data**: JSONB field for additional structured data
- **Time Zone Support**: TIMESTAMPTZ for accurate timestamp handling
- **Cross-Referencing**: Multiple ID fields for linking with other systems

### How to Use
- Add the `MonitoringLog` table to your Saleor database by running the SQL in `saleor/MonitoringLog.sql`.
- When logging events, store the `user_id`, `correlation_id`, and/or `vendor_id` in both the log entry and any related Saleor table records.
- To "attach" logs to Saleor data, simply query both tables using the shared IDs.
- No direct SQL joins are required; use the IDs for cross-reference in your application or analytics queries.

### Example Queries
```sql
-- Find all logs for a specific user
SELECT * FROM MonitoringLog WHERE user_id = '123e4567-e89b-12d3-a456-426614174000';

-- Get average latency by endpoint
SELECT endpoint, AVG(latency_ms) as avg_latency 
FROM MonitoringLog 
GROUP BY endpoint 
ORDER BY avg_latency DESC;

-- Find failed requests (status code >= 400)
SELECT * FROM MonitoringLog 
WHERE status_code >= 400 
ORDER BY created_at DESC;
```

This approach provides comprehensive API monitoring while maintaining flexibility for integration with Saleor's existing data structures. 