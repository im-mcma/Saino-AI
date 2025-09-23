# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
import logging

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseModel):
    """
    Manages all application settings and configurations.
    Reads from environment variables.
    """
    # FastAPI Settings
    PROJECT_NAME: str = "Saino Elite V7 - Titan"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_and_secure_key_for_jwt")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME: str = os.getenv("DB_NAME", "saino_elite_titan_db")
    
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        case_sensitive = True

settings = Settings()

# Configure logging
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(settings.PROJECT_NAME)
