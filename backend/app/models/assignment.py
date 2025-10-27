from enum import Enum
from app.db.base import Base
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import datetime
import uuid

class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


# Assignment History =>
# ticket_id = CASCADE
# team_member_id  = SET NULL

# Let's put the incoming tickets in Ticket Table => later => After resolved put it into Historical Tickets DB
# Or put the ticket in historical tickets and mention it here => Later ?
# When the ticket is resolved it must not been shown in frontend
# When the ticket is closed => current workload must also be resolved?

# when the ticket is closed it must be pushed to historical tickets ?
# Stored in historical tickets and updated it??


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Ai predictions
    assignment_by = Column(String(100), nullable=False)

    assigned_at = Column(DateTime, default=datetime.utcnow)
    best_assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    assignment_confidence = Column(Numeric(4, 3))
    assignment_reasoning = Column(Text)

    # priority

    # status => ??

    # task_type => ? Incident / Catalog Task

    # Relationship
    ticket = relationship("HistoricalTicket", back_populates="assignments")
    assignee = relationship("TeamMember", back_populates="assignments")

# Reassignment....
