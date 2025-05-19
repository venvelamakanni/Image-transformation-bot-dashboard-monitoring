


# Replace Background and Relight Microservice

This project is a FastAPI-based microservice that integrates with the Stability AI API to transform images. The primary functionality is to replace the background and relight a product image. The service accepts input images via S3 (or public URLs) and returns a transformed image after processing. The final image is uploaded back to an S3 bucket, and its object URL is returned as JSON.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Project Structure](#project-structure)
- [Running the Application](#running-the-application)
- [Usage Example](#usage-example)


## Features

- **Image Transformation:** Replace the background of an image and relight it using the Stability AI API.
- **S3 Integration:**  
  - Downloads input images from S3 (or public URLs) using AWS credentials.
  - Uploads the transformed image to a designated S3 bucket and returns its public URL.
- **Asynchronous Processing:** The API polls the Stability AI endpoint until the transformation is complete.
- **FastAPI Endpoint:** Provides a RESTful API that validates input using Pydantic models.

## Architecture

The project is structured into several modules:
- **FastAPI Application (`app/main.py`):** The entry point that initializes the FastAPI instance and includes API routes.
- **API Routes (`app/api.py`):** Defines the `/replace-background-relight` endpoint, which handles the image transformation workflow.
- **Pydantic Models (`app/models.py`):** Contains the `ReplaceBackgroundRelightInput` model used for input validation.
- **Utilities (`app/utils.py`):** Provides helper functions to:
  - Download images from S3 using AWS credentials.
  - Upload transformed images to S3.
  - Send asynchronous requests to the Stability AI API.
- **Configuration (`app/config.py`):** Loads environment variables (like AWS credentials, S3 bucket name, and Stability API key) from a `.env` file.

## Prerequisites

- Python 3.12 (or later)
- AWS account with an S3 bucket configured for private access
- AWS credentials (Access Key ID and Secret Access Key)
- Stability AI API key

## Installation and Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/replace-background-relight.git
   cd replace-background-relight
   ```

2. **Create a Virtual Environment and Activate It:**

   ```bash
   python -m venv .venv
   # On Linux/macOS:
   source .venv/bin/activate
   # On Windows (using Git Bash):
   source .venv/Scripts/activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables:**

   Create a `.env` file in the project root with the following contents (update the values accordingly):

   ```env
   STABILITY_KEY=your_stability_api_key
   S3_BUCKET=myawesomebucket
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_DEFAULT_REGION=us-east-1
   WORKER_TIMEOUT=500
   ```

   - `STABILITY_KEY`: Your Stability AI API key.
   - `S3_BUCKET`: Your S3 bucket name (e.g., "myawesomebucket").
   - `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: Your AWS credentials.
   - `AWS_DEFAULT_REGION`: Your bucket’s region (e.g., "us-east-1").
   - `WORKER_TIMEOUT`: Timeout in seconds for polling the Stability AI API.

## Project Structure

```
replace-background-relight/
├── app/
│   ├── __init__.py
│   ├── api.py               # Contains the FastAPI endpoint for image transformation.
│   ├── config.py            # Loads configuration from .env (AWS keys, bucket name, Stability API key).
│   ├── main.py              # Entry point to run the FastAPI app.
│   ├── models.py            # Pydantic models (input validation).
│   └── utils.py             # Helper functions for S3 integration and asynchronous API calls.
├── tests/                   # (Optional) Directory for test files.
│   └── test_api.py          # Example tests using pytest and FastAPI's TestClient.
├── requirements.txt         # Python dependencies.
├── .env                     # Environment variables (not checked into source control).
├── Dockerfile               # Dockerfile for containerizing the application.
├── README.md                # This file.
└── ...
```

## Running the Application

You can run the FastAPI application locally using Uvicorn:

```bash
uvicorn app.main:app --reload
```

- The application will be available at [http://localhost:8000](http://localhost:8000).
- Use the `/replace-background-relight` endpoint to post image transformation requests.


## Usage Example

Send a POST request to `/replace-background-relight` with a JSON payload similar to:

```json
{
  "subject_image": "https://myawesomebucket.s3.us-east-1.amazonaws.com/app/images/aquaphor.jpg",
  "background_prompt": "a smooth pink pastel backdrop",
  "background_reference": "https://myawesomebucket.s3.us-east-1.amazonaws.com/app/images/backdrop.jpg",
  "foreground_prompt": "",
  "negative_prompt": "",
  "preserve_original_subject": 0.95,
  "original_background_depth": 0.5,
  "keep_original_background": false,
  "light_source_strength": 0.3,
  "light_reference": "",
  "light_source_direction": "none",
  "seed": 42,
  "output_format": "png"
}
```

- The service will download the specified images from S3 using AWS credentials, send them to the Stability AI API, poll until processing is complete, then upload the transformed image to S3.
- The API will return a JSON response with the S3 URL of the transformed image:

  ```json
  {
    "s3_url": "https://myawesomebucket.s3.amazonaws.com/edited_image_42.png"
  }
  ```

