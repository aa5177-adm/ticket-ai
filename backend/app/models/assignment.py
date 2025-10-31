from app.db.base import Base
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid


class TicketAssignment(Base):
    """
    Ticket assignment history tracking.
    
    Tracks all assignments throughout a ticket's lifecycle:
    - Initial AI-based assignment when ticket arrives
    - Manual reassignments by admins
    - Assignment changes during ticket lifecycle
    
    Key Design:
    - While ticket is active: ticket_id is set, historical_ticket_id is NULL
    - When ticket archives: ticket_id becomes NULL, historical_ticket_id is set
    - Preserves complete assignment history for analytics and ML training
    """
    __tablename__ = "ticket_assignments"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    
    # For active tickets - points to tickets table
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,  # NULL after ticket archives
        index=True,
    )
    
    # For historical tickets - points to historical_tickets table
    # Set when ticket is archived
    historical_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tickets.id", ondelete="CASCADE"),
        nullable=True,  # NULL while ticket is active
        index=True,
    )

    # The team member assigned
    assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,  # Can be NULL if team member is deleted
        index=True,
    )

    # Assignment metadata
    assignment_by = Column(String(100), nullable=False)  # "AI", "Manual", "Reassignment"
    assigned_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    
    # AI prediction metadata (if assigned by AI)
    assignment_confidence = Column(Numeric(4, 3), nullable=True)  # 0.000 to 1.000
    assignment_reasoning = Column(Text, nullable=True)  # Why this assignee was chosen

    # Relationships
    ticket = relationship("Ticket", back_populates="assignments", foreign_keys=[ticket_id])
    historical_ticket = relationship("HistoricalTicket", back_populates="assignments", foreign_keys=[historical_ticket_id])
    assignee = relationship("TeamMember", back_populates="assignments")
    
    # Table constraints
    __table_args__ = (
        # Ensure EITHER ticket_id OR historical_ticket_id is set (XOR constraint)
        CheckConstraint(
            '(ticket_id IS NOT NULL AND historical_ticket_id IS NULL) OR '
            '(ticket_id IS NULL AND historical_ticket_id IS NOT NULL)',
            name='check_assignment_ticket_xor'
        ),
    )
