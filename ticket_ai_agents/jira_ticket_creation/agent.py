"""
Jira Ticket Creation Agent - Specialized agent for Jira integration
Date: November 4, 2025

This agent handles:
- Creating Jira tickets from internal tickets
- Synchronizing ticket data between systems
- Mapping internal fields to Jira fields
- Updating Jira tickets with latest information
- Managing cross-system ticket workflows
"""

from google.adk.agents import LlmAgent
from google.genai import types

from .prompt import JIRA_TICKET_CREATION_PROMPT

# Model configuration
MODEL = "gemini-2.0-flash-exp"

# Jira Ticket Creation Agent
jira_ticket_creation_agent = LlmAgent(
    name="jira_ticket_creation_agent",
    model=MODEL,
    description=(
        "Specialized agent for Jira story content creation. "
        "Creates new Jira stories, maps internal ticket fields to Jira format, "
        "requirements like issue types, priorities, and custom fields."
    ),
    instruction=JIRA_TICKET_CREATION_PROMPT,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,  # Lower temperature for accurate field mapping
        top_p=0.9,
        top_k=40,
    ),
    output_key="jira_sync_result",
)

__all__ = ["jira_ticket_creation_agent"]