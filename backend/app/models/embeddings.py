from sqlalchemy import Column, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid
from pgvector.sqlalchemy import Vector


class Embeddings(Base):
    """
    Embeddings table for ticket similarity search.
    
    Generated ONCE when ticket arrives (from title + description).
    Stays with the same ticket ID throughout its lifecycle (active → historical).
    
    Key Design:
    - Embedding generated immediately on ticket arrival
    - Used for AI assignment prediction (similarity search)
    - Ticket moves from active → historical with SAME UUID
    - Foreign key updates automatically when ticket archives
    """
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    
    # For active tickets - points to tickets table
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # For historical tickets - points to historical_tickets table
    # When ticket archives, ticket_id becomes NULL and historical_ticket_id gets set
    historical_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # The embedding vector (1536 dimensions for OpenAI embeddings)
    vector = Column(Vector(1536), nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="embedding", foreign_keys=[ticket_id])
    historical_ticket = relationship("HistoricalTicket", back_populates="embedding", foreign_keys=[historical_ticket_id])

    # Table arguments for indexing and constraints
    __table_args__ = (
        # Ensure EITHER ticket_id OR historical_ticket_id is set (XOR constraint)
        CheckConstraint(
            '(ticket_id IS NOT NULL AND historical_ticket_id IS NULL) OR '
            '(ticket_id IS NULL AND historical_ticket_id IS NOT NULL)',
            name='check_embedding_ticket_xor'
        ),
        # Index for fast lookup by ticket_id
        Index("idx_embeddings_ticket_id", "ticket_id"),
        # Index for fast lookup by historical_ticket_id
        Index("idx_embeddings_historical_ticket_id", "historical_ticket_id"),
        # Vector index for similarity search (IVFFlat algorithm)
        Index("idx_embeddings_vector", "vector", postgresql_using="ivfflat"),
    )
