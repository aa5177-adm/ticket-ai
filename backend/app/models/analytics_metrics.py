from sqlalchemy import Column, ForeignKey, DateTime, Integer, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid


class TicketProcessingMetrics(Base):
    """
    Metrics for tracking ticket processing performance.
    
    Tracks metrics for both active and historical tickets.
    - While ticket is active: ticket_id is set
    - When ticket archives: ticket_id becomes NULL, historical_ticket_id is set
    """
    
    __tablename__ = "ticket_processing_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    
    # For active tickets
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # For historical tickets (after archival)
    historical_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    processing_started_at = Column(DateTime, nullable=False)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration = Column(Integer, nullable=True)  # Duration in seconds
    analysis_duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Relationships
    ticket = relationship("Ticket", back_populates="processing_metrics", foreign_keys=[ticket_id])
    historical_ticket = relationship("HistoricalTicket", back_populates="processing_metrics", foreign_keys=[historical_ticket_id])

    # Table constraints
    __table_args__ = (
        # Ensure EITHER ticket_id OR historical_ticket_id is set (XOR constraint)
        CheckConstraint(
            '(ticket_id IS NOT NULL AND historical_ticket_id IS NULL) OR '
            '(ticket_id IS NULL AND historical_ticket_id IS NOT NULL)',
            name='check_metrics_ticket_xor'
        ),
        Index("idx_metrics_ticket_id", "ticket_id"),
        Index("idx_metrics_historical_ticket_id", "historical_ticket_id"),
    )
