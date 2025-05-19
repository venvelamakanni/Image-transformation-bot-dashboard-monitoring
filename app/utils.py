# app/utils.py
import os
import json
import time
import requests
import boto3
from fastapi import HTTPException
from io import BytesIO
from urllib.parse import urlparse
from app.config import STABILITY_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET
from app.logging_utils import setup_logging

logger = setup_logging("app.utils")

def send_async_generation_request(host: str, params: dict, files: dict = None):
    """
    Sends an asynchronous generation request to the Stability API.
    Polls until the generated image is ready.
    """
    logger.info(f"Preparing to send generation request to {host}")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }
    if files is None:
        files = {}

    # Process extra parameters "image" and "mask" if provided.
    image = params.pop("image", None)
    mask = params.pop("mask", None)
    if image is not None and image != '':
        try:
            files["image"] = open(image, 'rb')
            logger.info(f"Opened image file: {image}")
        except Exception as e:
            logger.error(f"Error opening image file: {image} - {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error opening image file: {image}, {e}")
    if mask is not None and mask != '':
        try:
            files["mask"] = open(mask, 'rb')
            logger.info(f"Opened mask file: {mask}")
        except Exception as e:
            logger.error(f"Error opening mask file: {mask} - {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error opening mask file: {mask}, {e}")
    if len(files) == 0:
        files["none"] = ''
        logger.info("No files provided; adding placeholder.")

    logger.info(f"Sending REST request to {host} with params: {params} and files: {list(files.keys())}")
    response = requests.post(host, headers=headers, files=files, data=params)
    if not response.ok:
        logger.error(f"Received error response: HTTP {response.status_code}: {response.text}")
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    logger.info("Received initial response from generation request.")
    response_dict = json.loads(response.text)
    generation_id = response_dict.get("id", None)
    if generation_id is None:
        logger.error("No generation id found in response.")
        raise Exception("Expected id in response")

    # Poll until result or timeout.
    timeout = int(os.getenv("WORKER_TIMEOUT", 500))
    start = time.time()
    status_code = 202
    poll_url = f"https://api.stability.ai/v2beta/results/{generation_id}"
    logger.info(f"Polling results at {poll_url}")
    while status_code == 202:
        logger.info(f"Polling at {poll_url}")
        response = requests.get(poll_url, headers={**headers, "Accept": "*/*"})
        if not response.ok:
            logger.error(f"Polling error: HTTP {response.status_code}: {response.text}")
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        status_code = response.status_code
        time.sleep(10)
        if time.time() - start > timeout:
            logger.error(f"Polling timed out after {timeout} seconds")
            raise Exception(f"Timeout after {timeout} seconds")
    logger.info("Polling completed successfully.")
    return response

def download_image(url: str) -> BytesIO:
    """
    Downloads an image from an S3 URL using AWS credentials and returns a BytesIO object.
    
    Assumes the object is in the bucket defined by S3_BUCKET. Only extracts the object key from the URL.
    
    Args:
        url (str): S3 object URL (e.g., "https://mybucket.s3.us-east-1.amazonaws.com/path/to/image.jpg")
    
    Returns:
        BytesIO: In-memory bytes buffer containing the image.
    
    Raises:
        HTTPException: If the object cannot be downloaded.
    """
    
    logger.info(f"Starting download for image: {url}")
    try:
        url = str(url)
        parsed = urlparse(url)
        key = parsed.path.lstrip('/')
        logger.info(f"Extracted S3 key: {key}")

        # Create the S3 client using credentials.
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )

        logger.info(f"Downloading image from bucket '{S3_BUCKET}', key: {key}")
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        content = response['Body'].read()
        logger.info(f"Downloaded image of size {len(content)} bytes")
        return BytesIO(content)
    except Exception as e:
        logger.error(f"Error downloading image from {url} - {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error downloading image from {url}: {e}")

def upload_bytes_to_s3(content: bytes, bucket_name: str, object_name: str) -> str:
    """
    Uploads binary image content to an S3 bucket and returns the object URL.
    """
    logger.info(f"Uploading file to S3: bucket='{bucket_name}', object_name='{object_name}'")
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(Body=content, Bucket=bucket_name, Key=object_name, ContentType='image/png')
        logger.info("File uploaded successfully to S3.")
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")
    url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
    logger.info(f"Constructed S3 URL: {url}")
    return url
