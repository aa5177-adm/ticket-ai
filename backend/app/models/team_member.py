from sqlalchemy import String, Column
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from enum import Enum
from app.db.base import Base
import uuid

class AppRole(str, Enum):
    """Supported roles in our application"""

    USER = "user"
    ADMIN = "admin"


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    coreid = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    role = Column(String(50), nullable=False)
    timezone = Column(String(50), nullable=False)
    app_role = Column(
        PgEnum(
            AppRole,
            name="app_role",  # Create PostgreSQL ENUM type => app_role
            create_type=False,  # Prevents re-creation if already exists (! Alembic)
        ),
        nullable=False,
    )

    # Relationships
    
    # Active tickets currently assigned
    active_tickets = relationship("Ticket", back_populates="assignee")
    
    # Historical tickets (resolved/closed)
    historical_tickets = relationship("HistoricalTicket", back_populates="assignee")

    # All assignments (both active and historical)
    assignments = relationship("TicketAssignment", back_populates="assignee")
    
    # Current workload tracking
    workload = relationship("TeamMemberWorkload", back_populates="member", uselist=False, cascade="all, delete-orphan")
    
    # Skills
    skills = relationship("TeamMemberSkill", back_populates="member", cascade="all, delete-orphan")
    
    # PTO and time off
    time_offs = relationship(
        "TimeOff",
        back_populates="member",
        cascade="all, delete-orphan",
    )
