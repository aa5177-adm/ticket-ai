from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# Pydantic model for a Ticket coming from ServiceNow
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
        "created_at": "2025-10-29T10:30:00Z",
        "due_date": "2025-11-05T10:30:00Z",
        "category": "GCP",
    }
    """
    event_type: str = Field(..., description="Event type from ServiceNow")
    ticket_id: str = Field(..., description="Unique ticket identifier")
    title: str = Field(..., description="Title of the ticket")
    description: str = Field(..., description="Detailed description of the ticket")
    priority: str = Field(..., description="Priority level of the ticket")
    status: str = Field(..., description="Current status of the ticket")
    caller_id: str = Field(..., description="Identifier of the caller")
    due_date: str = Field(..., description="Due date for the ticket resolution")
    category: Optional[str] = Field(None, description="Category of the ticket")
    created_at: Optional[str] = Field(None, description="Ticket creation timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
