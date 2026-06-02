import os

# Database Connection Settings
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback values if DATABASE_URL is not set
DB_HOST = os.getenv("DB_HOST", "/home/surya/data/pgdata")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "telugu_doc_db")
DB_USER = os.getenv("DB_USER", "surya")
DB_PASS = os.getenv("DB_PASS", "")

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Check if local development directory exists, fallback to repo data directory in production
if os.path.exists("/home/surya/project/auto"):
    JSON_DIR = os.getenv("JSON_DIR", "/home/surya/project/auto")
else:
    JSON_DIR = os.getenv("JSON_DIR", os.path.join(BASE_DIR, "data"))

IMAGES_DIR = os.getenv("IMAGES_DIR", os.path.join(JSON_DIR, "images"))

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8002"))
