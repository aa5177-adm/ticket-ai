# Import all models here for proper SQLAlchemy model registration and Alembic migrations
from app.db.base import Base
from app.models.team_member import TeamMember, AppRole
from app.models.ticket import Ticket, TicketStatus
from app.models.historical_tickets import HistoricalTicket, Priority
from app.models.assignment import TicketAssignment
from app.models.embeddings import Embeddings
from app.models.skills import Skill, TeamMemberSkill
from app.models.workload import TeamMemberWorkload
from app.models.pto_n_holiday import TimeOff, Holiday, TimeOffType, Region
from app.models.knowledge import KBArticle
from app.models.analytics_metrics import TicketProcessingMetrics
# from app.models.jira import (
#     JiraIntegration, 
#     JiraWebhookLog, 
#     JiraSyncHistory,
#     JiraIssueType,
#     JiraPriority,
#     JiraStatus
# )

__all__ = [
    "Base",
    # Team Member related
    "TeamMember",
    "AppRole",
    # Active Tickets
    "Ticket",
    "TicketStatus",
    # Historical Tickets
    "HistoricalTicket",
    "Priority",
    # Assignments
    "TicketAssignment",
    # Embeddings
    "Embeddings",
    # Skills
    "Skill",
    "TeamMemberSkill",
    # Workload
    "TeamMemberWorkload",
    # Time Off and Holidays
    "TimeOff",
    "Holiday",
    "TimeOffType",
    "Region",
    # Knowledge Base
    "KBArticle",
    # Analytics
    "TicketProcessingMetrics",
    # Jira Integration
    # "JiraIntegration",
    # "JiraWebhookLog", 
    # "JiraSyncHistory",
    # "JiraIssueType",
    # "JiraPriority",
    # "JiraStatus",
]
