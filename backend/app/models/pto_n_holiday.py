from enum import Enum
from app.db.base import Base
from sqlalchemy import Column, String, Date, ForeignKey, Index, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
import uuid

class TimeOffType(str, Enum):
    VACATION = "vacation"
    SICK = "sick"
    TRAINING = "training"
    CASUAL = "casual"
    OTHER = "other"


class Region(str, Enum):
    IN = "IN"
    US = "US"
    GLOBAL = "GLOBAL"


class TimeOff(Base):
    """Team member pto and time off"""

    __tablename__ = "time_offs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    member_id = Column(
        UUID(as_uuid=True),
        ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    type = Column(PgEnum(TimeOffType, name="timeoff_type", create_type=False))
    # Relationships
    member = relationship(
        "TeamMember", back_populates="time_offs", foreign_keys=[member_id]
    )

    __table_args__ = (
        Index("idx_timeoff_dates", "member_id", "start_date", "end_date"),
    )


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    title = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    date = Column(Date, nullable=False, index=True)
    region = Column(
        PgEnum(Region, name="region"),
        nullable=False,
        index=True
    )
    year = Column(Integer, nullable=False, index=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for regional holiday queries
        Index('idx_holidays_region_year', 'region', 'year'),
    )
