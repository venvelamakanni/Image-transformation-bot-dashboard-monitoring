import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from a .env file

STABILITY_KEY = os.getenv("STABILITY_KEY")
if not STABILITY_KEY:
    raise RuntimeError("STABILITY_KEY environment variable not set")
S3_BUCKET = os.getenv("S3_BUCKET")  # Set your S3 bucket name
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")