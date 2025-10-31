from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum


class Priority(str, Enum):
    CRITICAL = "1 - Critical"
    HIGH = "2 - High"
    MEDIUM = "3 - Medium"
    LOW = "4 - Low"
    PLANNING = "5 - Planning"


class HistoricalTicket(Base):
    """Historical tickets table - for resolved/closed tickets"""
    __tablename__ = "historical_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, unique=True)
    snow_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(PgEnum(Priority, name="priority", create_type=False))
    status = Column(String(50), nullable=False)  # Always "closed" or "resolved"
    resolution_notes = Column(Text, nullable=True)  # Store resolution details for KB generation
    created_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign Keys
    assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    assignee = relationship("TeamMember", back_populates="historical_tickets")

    # Assignment History
    assignments = relationship(
        "TicketAssignment",
        back_populates="historical_ticket",
        foreign_keys="TicketAssignment.historical_ticket_id",
        cascade="all, delete-orphan"
    )

    # Embedding (one-to-one, same UUID as ticket)
    embedding = relationship(
        "Embeddings",
        back_populates="historical_ticket",
        foreign_keys="Embeddings.historical_ticket_id",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Knowledge base articles generated from this ticket
    kb_articles = relationship(
        "KBArticle",
        back_populates="source_ticket",
        foreign_keys="KBArticle.source_ticket_id"
    )
    
    # Processing metrics for this ticket
    processing_metrics = relationship(
        "TicketProcessingMetrics",
        back_populates="historical_ticket",
        foreign_keys="TicketProcessingMetrics.historical_ticket_id",
        cascade="all, delete-orphan"
    )
    
    # Jira integration (one-to-one, preserved after archival)
    # jira_integration = relationship(
    #     "JiraIntegration",
    #     back_populates="historical_ticket",
    #     foreign_keys="JiraIntegration.historical_ticket_id",
    #     uselist=False,
    #     cascade="all, delete-orphan"
    # )
