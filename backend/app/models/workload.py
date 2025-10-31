from app.db.base import Base
from sqlalchemy import Column, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime


class TeamMemberWorkload(Base):
    __tablename__ = "team_member_workload"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    team_member_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("team_members.id", ondelete="CASCADE"),  # CASCADE: delete workload when member deleted
        unique=True, 
        nullable=False,  # Should not be NULL
        index=True
    )
    current_tickets = Column(Integer, nullable=False, server_default="0")
    max_tickets = Column(Integer, nullable=False, server_default="3")

    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    member = relationship("TeamMember", back_populates="workload")