from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum
from datetime import datetime
import uuid


class JiraIssueType(str, Enum):
    """Jira issue types"""
    STORY = "Story"
    EPIC = "Epic"

class JiraPriority(str, Enum):
    """Jira priority levels"""
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
class JiraStatus(str, Enum):
    """Common Jira status values"""
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    REVIEW = "In Review"
    DONE = "Done"

class JiraIntegration(Base):
    """
    Jira integration mapping for tickets.
    
    Links ServiceNow tickets to corresponding Jira issues for development tracking.
    Supports both active tickets and historical tickets through XOR constraint.
    
    Use Cases:
    - Track development work for ServiceNow incidents/requests
    - Sync status between ServiceNow and Jira
    - Analyze development effort vs ticket complexity
    - Report on cross-platform ticket lifecycle
    """
    __tablename__ = "jira_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    
    # Link to active tickets
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Link to historical tickets (after archival)
    historical_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Jira issue details
    jira_key = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "PROJ-123"
    jira_id = Column(String(50), nullable=False, index=True)  # Jira internal ID
    jira_url = Column(Text, nullable=True)  # Full URL to Jira issue
    
    # Issue metadata
    issue_type = Column(
        PgEnum(JiraIssueType, name="jira_issue_type", create_type=False),
        nullable=False
    )
    priority = Column(
        PgEnum(JiraPriority, name="jira_priority", create_type=False),
        nullable=True
    )
    status = Column(
        PgEnum(JiraStatus, name="jira_status", create_type=False),
        nullable=False
    )
    
    # Issue content
    summary = Column(String(500), nullable=False)  # Jira issue title
    description = Column(Text, nullable=True)  # Jira issue description
    
    # Assignee information
    jira_assignee_email = Column(String(255), nullable=True, index=True)
    jira_assignee_name = Column(String(255), nullable=True)
    
    # Project information
    project_key = Column(String(50), nullable=False, index=True)  # e.g., "PROJ"
    project_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    jira_created_at = Column(DateTime(timezone=True), nullable=True)  # When created in Jira

    
    # Development tracking
    story_points = Column(Integer, nullable=True)  # Estimated effort
    
    # Custom fields and metadata (flexible JSON storage)
    custom_fields = Column(JSONB, nullable=True)  # Store custom Jira field values
    labels = Column(JSONB, nullable=True)  # Jira labels array
    components = Column(JSONB, nullable=True)  # Jira components array
    
    
    # Relationships
    ticket = relationship("Ticket", back_populates="jira_integration")
    historical_ticket = relationship("HistoricalTicket", back_populates="jira_integration")
    
    # Table constraints and indexes
    __table_args__ = (
        # XOR constraint - must link to exactly one ticket type
        CheckConstraint(
            '(ticket_id IS NOT NULL AND historical_ticket_id IS NULL) OR '
            '(ticket_id IS NULL AND historical_ticket_id IS NOT NULL)',
            name='check_jira_ticket_xor'
        ),
    )
