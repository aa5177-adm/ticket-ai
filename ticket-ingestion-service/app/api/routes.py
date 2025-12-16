"""ServiceNow Webhook Routes"""

from fastapi import Request, BackgroundTasks, HTTPException, status, APIRouter, Header
from app.api.models import ServiceNowPayload
import hmac
import hashlib
import logging
from typing import Optional
from app.core.config import settings
from datetime import datetime
from app.core.publisher import TicketPublisher

logger = logging.getLogger(__name__)

webhook_router = APIRouter()
publisher = TicketPublisher()

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


def verify_hmac_signature(body: bytes, signature: Optional[str]) -> bool:
    """
    Validate HMAC signature from ServiceNow webhook.

    Args:
        body: Raw request body as bytes
        signature: Signature from X-ServiceNow-Signature header

    Returns:
        True if signature is valid
        
    Raises:
        HTTPException: If signature is missing or invalid
    """
    if not signature:
        logger.warning("Webhook request missing signature header")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-ServiceNow-Signature header"
        )

    try:
        secret = settings.SERVICENOW_WEBHOOK_SECRET.encode('utf-8')
        
        # Generate expected signature
        expected_signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_signature, signature):
            logger.warning("Invalid HMAC signature for webhook request")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )

        logger.debug("HMAC signature verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during HMAC verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signature verification failed"
        )

async def process_webhook_background(
    payload_dict: dict,
    webhook_id: str
) -> None:
    """
    Background task to process webhook asynchronously.
    
    Args:
        payload_dict: The validated payload dictionary
        webhook_id: Unique identifier for tracking this webhook
    """
    logger.info(f"[{webhook_id}] Starting background processing of webhook")
    
    try:
        # Publish ticket to Pub/Sub
        message_id = publisher.publish_ticket(payload_dict, webhook_id)
        logger.info(
            f"[{webhook_id}] Successfully published ticket '{payload_dict.get('number')}' "
            f"to Pub/Sub with message ID: {message_id}"
        )
    except Exception as e:
        logger.error(
            f"[{webhook_id}] Failed to publish ticket '{payload_dict.get('number')}' "
            f"to Pub/Sub: {e}",
            exc_info=True
        )
        # In production, consider implementing a dead-letter queue or retry mechanism

# Webhook endpoint
@webhook_router.post(
    "/webhook/servicenow",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
    summary="ServiceNow Webhook Endpoint",
    description="Receives webhook events from ServiceNow for ticket ingestion and publishes to Pub/Sub",
    responses={
        202: {"description": "Webhook accepted and queued for processing"},
        400: {"description": "Invalid request payload or unsupported event type"},
        403: {"description": "Invalid or missing signature"},
        500: {"description": "Internal server error"},
    },
)
async def receive_webhook(
    request: Request,
    payload: ServiceNowPayload,
    background_tasks: BackgroundTasks,
    x_servicenow_signature: Optional[str] = Header(None, alias="X-ServiceNow-Signature"),
) -> dict:
    """
    Webhook endpoint to receive and validate ServiceNow events.
    
    Args:
        request: FastAPI request object
        payload: Validated ServiceNow payload
        background_tasks: FastAPI background tasks
        x_servicenow_signature: HMAC signature from ServiceNow
        
    Returns:
        Success response with webhook ID
    """
    # Generate unique webhook ID for tracking
    webhook_id = f"webhook_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{payload.ticket_id}"
    
    try:
        # Log the incoming request
        logger.info(
            f"[{webhook_id}] Received webhook from ServiceNow - "
            f"Event: {payload.event_type}, Ticket: {payload.ticket_id}"
        )

        # Validate event type
        if payload.event_type not in ALLOWED_EVENT_TYPES:
            logger.warning(
                f"[{webhook_id}] Unsupported event type: {payload.event_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event type '{payload.event_type}' is not supported. "
                       f"Allowed types: {', '.join(sorted(ALLOWED_EVENT_TYPES))}"
            )

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

        return {
            "status": "accepted",
            "message": "Webhook received and queued for processing",
            "webhook_id": webhook_id,
            "ticket_number": payload.ticket_id
        }

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, auth errors)
        raise
    except Exception as e:
        logger.error(
            f"[{webhook_id}] Unexpected error processing webhook: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing webhook"
        )
