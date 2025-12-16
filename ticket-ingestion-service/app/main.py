from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import webhook_router
from app.core.publisher import TicketPublisher
import logging
from contextlib import asynccontextmanager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ServiceNow Ticket Ingestion Service")
    try:
        # Verify Pub/Sub connection on startup
        publisher = TicketPublisher()
        publisher.verify_connection()
        logger.info("Pub/Sub connection verified successfully")
    except Exception as e:
        logger.error(f"Failed to verify Pub/Sub connection: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ServiceNow Ticket Ingestion Service")

app = FastAPI(
    title="ServiceNow Ticket Ingestion Service",
    description="Microservice for ingesting ServiceNow tickets via webhooks and publishing to Google Cloud Pub/Sub",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware / if needed => If service now is server to server, CORS is not required -> HMAC is sufficient
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure based on your requirements
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(webhook_router, tags=["ServiceNow Webhook"])

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "service": "ServiceNow Ticket Ingestion Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        publisher = TicketPublisher()
        publisher.verify_connection()
        return {
            "status": "healthy",
            "pubsub": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "pubsub": "disconnected",
            "error": str(e)
        }