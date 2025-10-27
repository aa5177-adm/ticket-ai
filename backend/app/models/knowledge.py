from sqlalchemy import String, Column, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import relationship
from enum import Enum
from app.db.base import Base
import uuid

class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    title = Column(String(500), nullable=False),
    # root_cause = ?
    solution_steps = Column(Text, nullable=False)
    # similar articles found...

    # source ticket_id
    # helpful_count ?

# Tags Table?
# Article Tags ? => article id & tag_id