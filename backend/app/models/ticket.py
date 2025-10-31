from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.historical_tickets import Priority
from enum import Enum
import uuid


class TicketStatus(str, Enum):
    """Status for active tickets only"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


class Ticket(Base):
    """Active tickets table - for tickets currently being worked on"""
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    snow_id = Column(String(50), unique=True, nullable=False, index=True)
    caller_id = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(PgEnum(Priority, name="priority", create_type=False))
    status = Column(
        PgEnum(TicketStatus, name="ticket_status", create_type=False),
        nullable=False,
        default=TicketStatus.OPEN
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    
    # Current assignee
    assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Relationships
    assignee = relationship("TeamMember", back_populates="active_tickets")
    assignments = relationship(
        "TicketAssignment", 
        back_populates="ticket",
        foreign_keys="TicketAssignment.ticket_id",
        cascade="all, delete-orphan"
    )
    embedding = relationship(
        "Embeddings",
        back_populates="ticket",
        foreign_keys="Embeddings.ticket_id",
        uselist=False,
        cascade="all, delete-orphan"
    )
    processing_metrics = relationship(
        "TicketProcessingMetrics",
        back_populates="ticket",
        foreign_keys="TicketProcessingMetrics.ticket_id",
        cascade="all, delete-orphan"
    )
    
    # Jira integration (one-to-one)
    # jira_integration = relationship(
    #     "JiraIntegration",
    #     back_populates="ticket",
    #     foreign_keys="JiraIntegration.ticket_id",
    #     uselist=False,
    #     cascade="all, delete-orphan"
    # )
