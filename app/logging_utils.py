# app/logging_utils.py
import os
import logging
import json
import time
import uuid
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger
import asyncpg
from typing import Optional, Dict, Any

class DuplicateFilter(logging.Filter):
    """Filter that eliminates duplicate log messages within a time window."""
    
    def __init__(self, timeout=5):
        super().__init__()
        self.timeout = timeout
        self.last_log = {}
    
    def filter(self, record):
        key = (record.module, record.funcName, record.getMessage(), record.levelno)
        current_time = time.time()
        if key in self.last_log and (current_time - self.last_log[key] < self.timeout):
            return False
        self.last_log[key] = current_time
        return True

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add correlation ID if not present
        if not log_record.get('correlation_id'):
            log_record['correlation_id'] = str(uuid.uuid4())
        
        # Add worker ID
        log_record['worker_id'] = os.getpid()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add caller information
        log_record['caller'] = f"{record.module}.{record.funcName}:{record.lineno}"
        
        # Add any extra fields
        if hasattr(record, 'extra'):
            for key, value in record.extra.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    log_record[key] = value

def setup_logging(name: str):
    """
    Set up a logger with structured JSON formatting and duplicate log filtering.
    
    Environment variables:
      - LOG_LEVEL: Logging level (default: INFO)
      - LOG_DEDUP_TIMEOUT: Time in seconds to deduplicate duplicate log messages (default: 5)
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(getattr(logging, log_level))
    
    # Create console handler with JSON formatting
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    
    # Add duplicate filter
    dedup_timeout = int(os.getenv("LOG_DEDUP_TIMEOUT", "5"))
    handler.addFilter(DuplicateFilter(timeout=dedup_timeout))
    
    logger.addHandler(handler)
    logger.propagate = False
    return logger

def get_correlation_id():
    """Get or create a correlation ID for request tracing"""
    return str(uuid.uuid4())

async def log_to_database(
    pool: asyncpg.Pool,
    user_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    endpoint: str = "unknown",
    request_id: str = None,
    correlation_id: Optional[str] = None,
    level: str = "INFO",
    message: str = "",
    latency_ms: int = 0,
    status_code: int = 200,
    s3_url: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """Write log entry to the MonitoringLog table"""
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    if correlation_id is None:
        correlation_id = get_correlation_id()
    
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO MonitoringLog (
                user_id, vendor_id, endpoint, request_id, correlation_id,
                level, message, latency_ms, status_code, s3_url, extra_data
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, user_id, vendor_id, endpoint, request_id, correlation_id,
            level, message, latency_ms, status_code, s3_url, 
            json.dumps(extra_data) if extra_data else None)
