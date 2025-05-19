# app/api.py
import os
import uuid
import asyncio
import time
from fastapi import APIRouter, HTTPException, Request
from app.config import S3_BUCKET
from app.models import ReplaceBackgroundRelightInput
from app.utils import send_async_generation_request, download_image, upload_bytes_to_s3
from app.logging_utils import setup_logging, get_correlation_id
from app.metrics import (
    IMAGE_PROCESSING_DURATION,
    IMAGE_SIZE,
    S3_OPERATION_DURATION,
    STABILITY_API_DURATION,
    VENDOR_REQUESTS,
    ERROR_COUNTER
)

router = APIRouter()
logger = setup_logging("app.api")

REPLACE_BACKGROUND_RELIGHT_ENDPOINT = "https://api.stability.ai/v2beta/stable-image/edit/replace-background-and-relight"

@router.post("/replace-background-relight")
async def replace_background_relight(request: Request, input: ReplaceBackgroundRelightInput):
    correlation_id = get_correlation_id()
    start_time = time.time()
    vendor_id = input.username or "anonymous"
    
    logger.info("Received request", extra={
        "correlation_id": correlation_id,
        "vendor_id": vendor_id,
        "input": input.model_dump()
    })
    
    VENDOR_REQUESTS.labels(vendor_id=vendor_id, operation_type="replace_background_relight").inc()
    
    try:
        # Download input images from S3/public URLs using async wrappers.
        with IMAGE_PROCESSING_DURATION.labels(operation_type="download_subject").time():
            try:
                subject_file = await asyncio.to_thread(download_image, input.subject_image)
                IMAGE_SIZE.labels(operation_type="subject").observe(len(subject_file))
                logger.info("Downloaded subject image", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "subject_image": input.subject_image
                })
            except Exception as e:
                ERROR_COUNTER.labels(error_type="download_subject", vendor_id=vendor_id).inc()
                logger.error("Error downloading subject image", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "error": str(e)
                })
                raise HTTPException(status_code=400, detail=str(e))
        
        files = {
            "subject_image": ("subject_image", subject_file, "application/octet-stream")
        }
        
        if input.background_reference:
            with IMAGE_PROCESSING_DURATION.labels(operation_type="download_background").time():
                try:
                    background_file = await asyncio.to_thread(download_image, input.background_reference)
                    IMAGE_SIZE.labels(operation_type="background").observe(len(background_file))
                    files["background_reference"] = ("background_reference", background_file, "application/octet-stream")
                    logger.info("Downloaded background image", extra={
                        "correlation_id": correlation_id,
                        "vendor_id": vendor_id,
                        "background_reference": input.background_reference
                    })
                except Exception as e:
                    ERROR_COUNTER.labels(error_type="download_background", vendor_id=vendor_id).inc()
                    logger.error("Error downloading background image", extra={
                        "correlation_id": correlation_id,
                        "vendor_id": vendor_id,
                        "error": str(e)
                    })
                    raise HTTPException(status_code=400, detail=str(e))
        
        if input.light_reference:
            with IMAGE_PROCESSING_DURATION.labels(operation_type="download_light").time():
                try:
                    light_file = await asyncio.to_thread(download_image, input.light_reference)
                    IMAGE_SIZE.labels(operation_type="light").observe(len(light_file))
                    files["light_reference"] = ("light_reference", light_file, "application/octet-stream")
                    logger.info("Downloaded light reference image", extra={
                        "correlation_id": correlation_id,
                        "vendor_id": vendor_id,
                        "light_reference": input.light_reference
                    })
                except Exception as e:
                    ERROR_COUNTER.labels(error_type="download_light", vendor_id=vendor_id).inc()
                    logger.error("Error downloading light reference image", extra={
                        "correlation_id": correlation_id,
                        "vendor_id": vendor_id,
                        "error": str(e)
                    })
                    raise HTTPException(status_code=400, detail=str(e))
        
        # Prepare parameters for the Stability API.
        params = {
            "output_format": input.output_format,
            "background_prompt": input.background_prompt,
            "foreground_prompt": input.foreground_prompt,
            "negative_prompt": input.negative_prompt,
            "preserve_original_subject": input.preserve_original_subject,
            "original_background_depth": input.original_background_depth,
            "keep_original_background": input.keep_original_background,
            "seed": input.seed
        }
        if input.light_source_direction != "none":
            params["light_source_direction"] = input.light_source_direction
        if input.light_source_direction != "none" or input.light_reference:
            params["light_source_strength"] = input.light_source_strength

        logger.info("Prepared Stability API parameters", extra={
            "correlation_id": correlation_id,
            "vendor_id": vendor_id,
            "params": params
        })
        
        # Call the asynchronous generation API.
        with STABILITY_API_DURATION.labels(operation_type="generation").time():
            try:
                api_response = await asyncio.to_thread(send_async_generation_request, REPLACE_BACKGROUND_RELIGHT_ENDPOINT, params, files)
                logger.info("Received response from Stability API", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "status_code": api_response.status_code
                })
            except Exception as e:
                ERROR_COUNTER.labels(error_type="stability_api", vendor_id=vendor_id).inc()
                logger.error("Error during generation API call", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "error": str(e)
                })
                raise HTTPException(status_code=500, detail=str(e))
        
        if api_response.status_code != 200:
            ERROR_COUNTER.labels(error_type="stability_api_error", vendor_id=vendor_id).inc()
            logger.error("Stability API error", extra={
                "correlation_id": correlation_id,
                "vendor_id": vendor_id,
                "status_code": api_response.status_code,
                "response": api_response.text
            })
            raise HTTPException(status_code=api_response.status_code, detail=f"Stability API error: {api_response.text}")
        
        finish_reason = api_response.headers.get("finish-reason")
        if finish_reason == 'CONTENT_FILTERED':
            ERROR_COUNTER.labels(error_type="nsfw_filter", vendor_id=vendor_id).inc()
            logger.error("Generation failed NSFW classifier", extra={
                "correlation_id": correlation_id,
                "vendor_id": vendor_id
            })
            raise HTTPException(status_code=400, detail="Generation failed NSFW classifier")
        
        # Create a unique filename.
        unique_part = str(uuid.uuid4())
        if input.username:
            filename = f"{input.username}_{unique_part}.{input.output_format}"
        else:
            filename = f"{unique_part}.{input.output_format}"
        object_name = f"transformed_images/{filename}"
        logger.info("Generated unique filename", extra={
            "correlation_id": correlation_id,
            "vendor_id": vendor_id,
            "unique_filename": filename
        })
        
        # Upload the transformed image to S3 asynchronously.
        with S3_OPERATION_DURATION.labels(operation_type="upload").time():
            try:
                s3_url = await asyncio.to_thread(upload_bytes_to_s3, api_response.content, S3_BUCKET, object_name)
                IMAGE_SIZE.labels(operation_type="output").observe(len(api_response.content))
                logger.info("Uploaded image to S3", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "s3_url": s3_url
                })
            except Exception as e:
                ERROR_COUNTER.labels(error_type="s3_upload", vendor_id=vendor_id).inc()
                logger.error("Error uploading image to S3", extra={
                    "correlation_id": correlation_id,
                    "vendor_id": vendor_id,
                    "error": str(e)
                })
                raise HTTPException(status_code=500, detail=str(e))
        
        processing_time = time.time() - start_time
        logger.info("Request completed", extra={
            "correlation_id": correlation_id,
            "vendor_id": vendor_id,
            "processing_time": processing_time,
            "s3_url": s3_url
        })
        
        return {"s3_url": s3_url}
        
    except Exception as e:
        ERROR_COUNTER.labels(error_type="unknown", vendor_id=vendor_id).inc()
        logger.error("Unexpected error", extra={
            "correlation_id": correlation_id,
            "vendor_id": vendor_id,
            "error": str(e)
        })
        raise
