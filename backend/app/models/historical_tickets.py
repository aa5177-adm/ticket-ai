from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
from enum import Enum
import uuid


class Priority(str, Enum):
    CRITICAL = "1 - Critical"
    HIGH = "2 - High"
    MEDIUM = "3 - Medium"
    LOW = "4 - Low"
    PLANNING = "5 - Planning"


class HistoricalTicket(Base):
    __tablename__ = "historical_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    snow_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(PgEnum(Priority, name="priority", create_type=False))
    status = Column(String(50), nullable=False)
    # metadata =
    created_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign Keys
    assignee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    assignee = relationship("TeamMember", back_populates="tickets")

    # Assignment History?

    # Embeddings
    embeddings = relationship(
        "Embeddings", back_populates="ticket_embeddings", cascade="all, delete-orphan"
    )
