"""
Processing Service - Production-grade FastAPI application for handling Pub/Sub messages.
"""
import json
import base64
import logging
import sys
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from pythonjsonlogger import jsonlogger

from .config import settings


# Configure structured logging
def setup_logging():
    """Configure structured JSON logging for production."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


logger = setup_logging()


# Pydantic models for request validation
class PubSubMessage(BaseModel):
    """Pub/Sub message structure."""
    data: str
    messageId: str = Field(default="", alias="messageId")
    publishTime: str = Field(default="", alias="publishTime")
    attributes: Dict[str, str] = Field(default_factory=dict)


class PubSubEnvelope(BaseModel):
    """Pub/Sub envelope structure."""
    message: PubSubMessage
    subscription: str = ""


class TicketData(BaseModel):
    """Ticket data structure."""
    ticket_id: str
    # Add additional fields as needed for your use case


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info(
        "Application starting",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment
        }
    )
    yield
    logger.info("Application shutting down")


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Add middleware
# app.add_middleware(GZipMiddleware, minimum_size=1000)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Configure appropriately for your use case
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


def process_ticket_data(ticket: TicketData) -> None:
    """
    Process ticket data with AI and backend functionalities.
    
    Args:
        ticket: Validated ticket data
        
    Raises:
        Exception: If processing fails
    """
    logger.info(
        "Starting AI processing",
        extra={
            "ticket_id": ticket.ticket_id,
            "ticket_details": ticket.model_dump()
        }
    )
    
    # TODO: Implement actual AI processing logic here
    # This is where you would:
    # - Call AI services
    # - Process business logic
    # - Update databases
    # - Send notifications, etc.
    
    logger.info(
        "AI processing completed",
        extra={"ticket_id": ticket.ticket_id}
    )


@app.post("/process_ticket", status_code=status.HTTP_204_NO_CONTENT)
async def receive_pubsub_message(request: Request) -> None:
    """
    Receive and process a push message from a Pub/Sub subscription.
    
    This endpoint is designed to work with Google Cloud Pub/Sub push subscriptions.
    It validates the message format, decodes the payload, and processes the ticket data.
    
    Args:
        request: FastAPI request object containing the Pub/Sub message
        
    Returns:
        None (204 No Content on success)
        
    Raises:
        HTTPException: If the message format is invalid or processing fails
    """
    try:
        # Parse and validate the envelope
        envelope_data = await request.json()
        envelope = PubSubEnvelope(**envelope_data)
        
        logger.info(
            "Received Pub/Sub message",
            extra={
                "message_id": envelope.message.messageId,
                "subscription": envelope.subscription
            }
        )
        
        # Decode the base64-encoded data
        data_bytes = base64.b64decode(envelope.message.data)
        ticket_dict = json.loads(data_bytes.decode("utf-8"))
        
        # Validate ticket data
        ticket_data = TicketData(**ticket_dict)
        
        logger.info(
            "Successfully decoded ticket data",
            extra={"ticket_id": ticket_data.ticket_id}
        )
        
        # Process the ticket
        process_ticket_data(ticket_data)
        
        logger.info(
            "Successfully processed ticket",
            extra={"ticket_id": ticket_data.ticket_id}
        )
        
        return
        
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to decode JSON data",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON data in message"
        )
        
    except base64.binascii.Error as e:
        logger.error(
            "Failed to decode base64 data",
            extra={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64-encoded data"
        )
        
    except Exception as e:
        logger.error(
            "Error processing ticket",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True
        )
        # Return 5xx to trigger Pub/Sub retry
        # Consider implementing a dead-letter queue for repeatedly failing messages
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process message"
        )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for container orchestration platforms.
    
    Returns:
        Dict containing the service status
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }
     