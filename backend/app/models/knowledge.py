from sqlalchemy import String, Column, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    title = Column(String(500), nullable=False)
    root_cause = Column(Text, nullable=True)
    solution_steps = Column(Text, nullable=False)
    
    # Source ticket reference
    source_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Helpful count for rating
    helpful_count = Column(Integer, default=0, nullable=False)
    
    # Relationship
    source_ticket = relationship(
        "HistoricalTicket",
        back_populates="kb_articles",
        foreign_keys=[source_ticket_id]
    )

# Tags Table?
# Article Tags ? => article id & tag_id