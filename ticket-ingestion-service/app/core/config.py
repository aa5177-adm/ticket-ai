from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pydantic_settings import SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file"""
    
    # GCP Configuration
    GCP_PROJECT_ID: str = Field(
        ...,
        description="Google Cloud Project ID",
    )
    PUBSUB_TOPIC_ID: str = Field(
        ...,
        description="Google Cloud Pub/Sub Topic ID for publishing tickets",
    )
    
    # ServiceNow Configuration
    SERVICENOW_WEBHOOK_SECRET: str = Field(
        ...,
        description="Secret key for validating ServiceNow webhook HMAC signatures",
        min_length=16
    )
    
    # Optional Configuration
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    MAX_RETRIES: int = Field(
        default=3,
        description="Maximum number of retry attempts for Pub/Sub publish",
        ge=0,
        le=10
    )
    PUBLISH_TIMEOUT: float = Field(
        default=10.0,
        description="Timeout for Pub/Sub publish operations in seconds",
        gt=0
    )

    @field_validator('GCP_PROJECT_ID', 'PUBSUB_TOPIC_ID')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure critical fields are not empty"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        valid_envs = {'development', 'staging', 'production'}
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of {valid_envs}")
        return v_lower

    @field_validator('SERVICENOW_WEBHOOK_SECRET')
    @classmethod
    def validate_webhook_secret(cls, v: str) -> str:
        """Validate webhook secret meets security requirements"""
        if not v or not v.strip():
            raise ValueError("SERVICENOW_WEBHOOK_SECRET cannot be empty")
        if len(v.strip()) < 16:
            raise ValueError("SERVICENOW_WEBHOOK_SECRET must be at least 16 characters long")
        return v.strip()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env
        validate_default=True
    )

# Initialize settings with better error handling
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"❌ Configuration Error: {e}")
    print("\n💡 Tips:")
    print("  - For local development: Create a .env file with required variables")
    print("  - For Cloud Run: Ensure secrets are configured with --set-secrets")
    print("  - Check SECRETS_MANAGEMENT.md for setup instructions")
    sys.exit(1)