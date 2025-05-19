from fastapi import FastAPI
from app.api import router
from app.metrics import setup_metrics
from app.logging_utils import setup_logging

logger = setup_logging("app.main")

app = FastAPI(
    title="Image Transformation API",
    description="API for transforming images using Stability AI",
    version="1.0.0"
)

# Setup metrics
setup_metrics(app)

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include API router
app.include_router(router, prefix="/api/v1")

logger.info("Application started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
