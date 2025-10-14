from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    VERSION: str = "1.0.0"
    API_VERSION: str = "v1"
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    GCP_PROJECT_ID: str

    class Config:
        env_file = ".env"

settings = Settings()