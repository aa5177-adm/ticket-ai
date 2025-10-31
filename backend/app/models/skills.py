from app.db.base import Base
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)

    # Relationship
    member_skills = relationship("TeamMemberSkill", back_populates="skill", cascade="all, delete-orphan")
    

class TeamMemberSkill(Base):
    __tablename__ = "team_member_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationship
    skill = relationship("Skill", back_populates="member_skills")
    member = relationship("TeamMember", back_populates="skills")
    