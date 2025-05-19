from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Custom metrics
IMAGE_PROCESSING_DURATION = Histogram(
    "image_processing_duration_seconds",
    "Time spent processing images",
    ["operation_type"]
)

IMAGE_SIZE = Histogram(
    "image_size_bytes",
    "Size of processed images",
    ["operation_type"]
)

S3_OPERATION_DURATION = Histogram(
    "s3_operation_duration_seconds",
    "Time spent on S3 operations",
    ["operation_type"]
)

STABILITY_API_DURATION = Histogram(
    "stability_api_duration_seconds",
    "Time spent on Stability API calls",
    ["operation_type"]
)

VENDOR_REQUESTS = Counter(
    "vendor_requests_total",
    "Total number of requests per vendor",
    ["vendor_id", "operation_type"]
)

ERROR_COUNTER = Counter(
    "error_total",
    "Total number of errors",
    ["error_type", "vendor_id"]
)

def setup_metrics(app):
    """Setup Prometheus metrics for the application"""
    
    # Initialize the instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="fastapi_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(metrics.default())

    # Add custom metrics
    @instrumentator.instrument()
    def custom_metrics(info: Info) -> None:
        # Add any custom metrics here
        pass

    # Instrument the app
    instrumentator.instrument(app).expose(app) 