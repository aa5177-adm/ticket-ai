"""Snow Webhook"""

from fastapi import Request, BackgroundTasks, HTTPException, Depends, APIRouter, Header
from pydantic import BaseModel, Field
import hmac
import hashlib
import logging
from typing import Optional
from app.core.config import settings
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

webhook_router = APIRouter()

ALLOWED_EVENT_TYPES = {
    "incident.created",
    "incident.closed",
    "incident.resolved",
    # "incident.reassigned",
    "task.created",
    "task.closed",
    "task.resolved",
    # "task.reassigned",
}


class ServiceNowPayload(BaseModel):
    """
    ServiceNow webhook payload model with validation.
    
    Expected payload structure from ServiceNow:
    {
        "event_type": "incident.created",
        "number": "INC0012345",
        "caller": "Caller_name",
        "state": "open",
        "priority": "3",
        "short_description": "Ticket title",
        "description": "Full description",
        "created_at": "2025-10-29T10:30:00Z"
    }
    """
    event_type: str = Field(..., description="Event type from ServiceNow")
    number: str = Field(..., description="Ticket number, e.g., INC0012345")
    caller: str = Field(..., description="Caller name or ID")
    priority: str = Field(..., description="Priority level(1-5)")
    state: str = Field(..., description="Open/Closed")
    short_description: str = Field(..., description="Short description of the ticket")
    description: str = Field(..., description="Full description of the ticket")
    created_at: str = Field(..., description="Creation timestamp")

def verify_hmac_signature(body: bytes, signature: str) -> bool:
    """
    Validate HMAC signature from ServiceNow webhook.

    Args:
        body_bytes: Raw request body as bytes
        signature: Signature from X-ServiceNow-Signature header

    Returns:
        True if signature is valid
    """

    if not signature:
        logger.warning("Webhook request missing signature header")
        raise HTTPException(
            status_code=403, detail="Missing X-ServiceNow-Signature header"
        )

    secret = settings.SERVICENOW_WEBHOOK_SECRET.encode('utf-8')
    logger.info(f"Secret: {secret}")

    # Compare the generated signature with the one from the header
    expected_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

    # constant-time comparison
    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Invalid HMAC signature for webhook request")
        raise HTTPException(status_code=403, detail="Invalid signature")

    logger.info("HMAC signature verified successfully")
    return True

async def process_webhook_background(
    payload_dict: dict,
    webhook_id: str
):
#    """Background task to process webhook asynchronously"""
    pass


# Webhook endpoint
@webhook_router.post(
    "/webhook/servicenow",
    status_code=202,
    response_model=dict,
    summary="ServiceNow Webhook Endpoint",
    description="Receives webhook events from ServiceNow for ticket assignment",
)
async def receive_webhook(
    request: Request,
    payload: ServiceNowPayload,
    background_tasks: BackgroundTasks,
    x_servicenow_signature: Optional[str] = Header(None),
):
    """Webhook endpoint to receive data from ServiceNow"""

    # Generate unique webhook ID for tracking
    webhook_id = f"webhook_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{payload.number}"
    try:
        # Log the incoming request
        logger.info(f"[{webhook_id}] Received webhook from ServiceNow")

        # Read the raw body for signature validation
        raw_body = await request.body() # bytes

        # Verify HMAC signature
        verify_hmac_signature(raw_body, x_servicenow_signature)

        # Add background task for async processing
        background_tasks.add_task(
            process_webhook_background,
            payload_dict=payload.model_dump(),
            webhook_id=webhook_id
        )

        logger.info(f"[{webhook_id}] Webhook queued for background processing")


        return {"status": "success", "message": "Webhook received successfully!"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
