"""Configuration management for the processing service."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Processing Service"
    app_version: str = "1.0.0"
    environment: str = "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
