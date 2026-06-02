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
PROJECT_ROOT = "/home/surya/project"
JSON_DIR = os.getenv("JSON_DIR", os.path.join(PROJECT_ROOT, "auto"))
IMAGES_DIR = os.getenv("IMAGES_DIR", os.path.join(JSON_DIR, "images"))

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8002"))  # Using 8002 to avoid clash with other running APIs
