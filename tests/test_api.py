# test_api.py
import os
from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Dummy response class to simulate external API responses.
class DummyResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")

# Dummy function to simulate the Stability API call.
def dummy_send_async_generation_request(host, params, files):
    # Simulate image generation by returning dummy PNG bytes.
    dummy_image_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    # Include a finish reason header to simulate success.
    headers = {"finish-reason": "SUCCESS"}
    return DummyResponse(dummy_image_data, status_code=200, headers=headers)

# Dummy function to simulate uploading bytes to S3.
def dummy_upload_bytes_to_s3(content, bucket_name, object_name):
    # Return a fake S3 URL based on the bucket and object name.
    return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"

# Dummy function to simulate downloading an image.
def dummy_download_image(url):
    # Return a BytesIO with dummy PNG data.
    return BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

def test_replace_background_relight(monkeypatch):
    # Patch functions in the utils module.
    from app import api
    monkeypatch.setattr(api, "send_async_generation_request", dummy_send_async_generation_request)
    monkeypatch.setattr(api, "upload_bytes_to_s3", dummy_upload_bytes_to_s3)
    monkeypatch.setattr(api, "download_image", dummy_download_image)

    
    # Construct a valid JSON payload.
    payload = {
      "subject_image": "https://example.com/example.png",
      "background_prompt": "a smooth pink pastel backdrop",
      "background_reference": "https://example.com/backdrop.jpg",
      "foreground_prompt": "",
      "negative_prompt": "",
      "preserve_original_subject": 0.95,
      "original_background_depth": 0.5,
      "keep_original_background": False,
      "light_source_strength": 0.3,
      "light_reference": "https://example.com/light.png",
      "light_source_direction": "none",
      "seed": 42,
      "output_format": "png",
      "username": "user1"
    }
    
    response = client.post("/replace-background-relight", json=payload)
    
    # Check that the endpoint returns HTTP 200 and the JSON contains the S3 URL.
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    json_resp = response.json()
    assert "s3_url" in json_resp, "Response JSON does not contain 's3_url'"
    assert json_resp["s3_url"].startswith("https://"), "S3 URL does not start with 'https://'"

