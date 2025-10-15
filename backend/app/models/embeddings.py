from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from pgvector.sqlalchemy import Vector

class Embeddings(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("historical_tickets.id", ondelete="CASCADE"), nullable=False)
    vector = Column(Vector(1536), nullable=False)

    # Relationship
    ticket_embeddings = relationship("HistoricalTicket", back_populates="embeddings")

    # Table arguments for indexing and constraints
    __table_args__ = (
        Index("ix_embeddings_ticket_id", "ticket_id"), # Index for fast lookup by ticket_id
        Index("ix_embeddings_vector", "vector", postgresql_using="ivfflat") # Index for vector similarity search
    )
    """
    Indexing
        ticket_id Index: Added an index on ticket_id for faster queries when filtering embeddings by ticket.
        vector Index: Added a vector index for similarity search using pgvector. 
        This is specific to PostgreSQL and improves performance for operations like nearest neighbor search.
    """