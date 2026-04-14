"""
Client-side configuration loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

# Port used by the local OAuth callback server
AUTH0_CALLBACK_PORT: int = int(os.getenv("AUTH0_CALLBACK_PORT", "8080"))
