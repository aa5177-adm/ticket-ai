"""
Ticket Assignment Agent - Specialized agent for ticket triage and assignment
Date: November 4, 2025

This agent handles:
- Ticket priority analysis
- Skill requirement identification
- Team member matching
- Workload balancing
- Assignment decision making
"""

from google.adk.agents import LlmAgent
from google.genai import types
from typing import Optional
from datetime import datetime
from google.adk.agents.callback_context import CallbackContext
from ticket_ai_agents.tools.database_tools import get_team_member_by_email
from ticket_ai_agents.tools.generate_embedding import generate_ticket_embedding
from ticket_ai_agents.tools.search_similar_tickets import search_similar_tickets
from ticket_ai_agents.tools.assign_ticket import assign_ticket_with_engine

# from .prompt import TICKET_ASSIGNMENT_PROMPT

# Model configuration
MODEL = "gemini-2.5-flash"

# Ticket Assignment Agent
# ticket_assignment_agent = LlmAgent(
#     name="ticket_assignment_agent",
#     model=MODEL,
#     description=(
#         "Specialized agent for ticket triage, priority analysis, and intelligent assignment. "
#         "Analyzes ticket content to determine priority, identifies required skills, "
#         "matches with appropriate team members based on expertise, availability, and workload. "
#         "Provides optimal assignment recommendations."
#     ),
#     instruction=TICKET_ASSIGNMENT_PROMPT,
#     generate_content_config=types.GenerateContentConfig(
#         temperature=0.3,  # Lower temperature for consistent triage decisions
#         top_p=0.9,
#         top_k=40,
#     ),
#     output_key="assignment_result",
# )

# Defining callback function to output the state

def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback function that logs when the agent starts processing a request.
    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """

    # Get the session state
    state = callback_context.state

    # Record timestamp
    timestamp = datetime.now()

    print("=== AGENT EXECUTION STARTED ===")
    
    # Safe state access with error handling
    ticket_details = state.get("current_ticket_details", {})
    print(f"State Contents: {ticket_details}")

    # state_dict = {}
    # if hasattr(state, '__iter__'):
    #     for key in state:
    #         state_dict[key] = state.get(key)

    # Properly iterate and display state contents
    # State object supports dictionary-like access but needs manual iteration
    # print("State Contents:")
    # try:
    #     # Get a specific key if it exists
    #     if "current_ticket_details" in state:
    #         print(f"  current_ticket_details: {state.get('current_ticket_details')}")
    #     if "current_ticket_id" in state:
    #         print(f"  current_ticket_id: {state.get('current_ticket_id')}")
    #     if "last_action" in state:
    #         print(f"  last_action: {state.get('last_action')}")
        
    #     # Show all keys (if state has any)
    #     # Note: State object may not support direct iteration in all cases
    #     print(f"  [State object: {state}]")
    # except Exception as e:
    #     print(f"  Unable to fully display state: {e}")
    
    print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    return None

def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback that logs when the agent finishes processing a request.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    # Get the session state
    state = callback_context.state

    # Calculate request duration if start time is available
    timestamp = datetime.now()
    
    print("=== AGENT EXECUTION FINISHED ===")
    # Safe state access with error handling
    state_dict = {}
    if hasattr(state, '__iter__'):
        for key in state:
            state_dict[key] = state.get(key)
    print(f"State Contents: {state_dict}")


    # Properly iterate and display state contents
    # print("State Contents:")
    # try:
    #     # Get specific keys if they exist
    #     if "current_ticket_details" in state:
    #         print(f"  current_ticket_details: {state.get('current_ticket_details')}")
    #     if "current_ticket_id" in state:
    #         print(f"  current_ticket_id: {state.get('current_ticket_id')}")
    #     if "last_action" in state:
    #         print(f"  last_action: {state.get('last_action')}")
        
    #     # Show state object reference
    #     print(f"  [State object: {state}]")
    # except Exception as e:
    #     print(f"  Unable to fully display state: {e}")
    
    print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    return None


ticket_assignment_agent = LlmAgent(
    name="ticket_assignment_agent",
    model=MODEL,
    description=(
        "Specialized agent for ticket triage, priority analysis, and intelligent assignment. "
        "Analyzes ticket content to determine priority, identifies required skills, "
        "matches with appropriate team members using a sophisticated multi-factor assignment engine. "
        "Generates embeddings for ticket content to enable similarity-based matching. "
        "Uses customized assignment algorithm considering similarity, skills, availability, workload, and timezone."
    ),
    instruction="""Your task is to analyze tickets and make intelligent assignment decisions using the customized assignment engine.
    
    ## Standard Workflow:
    1. **Generate Embedding**: Call 'generate_ticket_embedding' to create vector representation
    2. **Search Similar Tickets**: Call 'search_similar_tickets' to find historical patterns
    3. **Assign Ticket**: Call 'assign_ticket_with_engine' to run the sophisticated assignment algorithm
    
    The assignment engine will automatically:
    - Evaluate all team members across 5 dimensions (similarity, skills, availability, workload, timezone)
    - Apply business rules (overload prevention, fair distribution, timezone routing)
    - Calculate confidence and provide detailed reasoning
    - Handle global holidays intelligently (Critical: emergency override, Medium/Low: wait)
    
    ## Available Tools:
    - **generate_ticket_embedding**: Generates 768-dimensional embedding for ticket title and description
      - Use this FIRST when a new ticket is being processed
      - Can work in two modes:
        * **State Mode**: Reads from state if ticket details are already stored
        * **Direct Mode**: Pass ticket_title, ticket_description, ticket_category as parameters
      - If user provides ticket info in their message, extract it and pass as parameters:
        generate_ticket_embedding(
            ticket_title="extracted title",
            ticket_description="extracted description",
            ticket_category="extracted category"
        )
      - The embedding is stored in state and can be used for similarity matching
      - Returns success status and embedding metadata
    
    - **search_similar_tickets**: Search for similar historical tickets using embedding similarity
      - Use this AFTER generating embedding for the current ticket
      - Finds historically resolved tickets with similar content
      - Parameters:
        * top_k: Number of similar tickets to retrieve (default: 5)
        * similarity_threshold: Minimum similarity score 0.0-1.0 (default: 0.70)
        * category_filter: Optional category filter (e.g., "AWS", "Database")
        * only_resolved: Search only resolved tickets (default: True)
      - Returns similar tickets with:
        * similarity_score: How similar (0.0-1.0, higher = more similar)
        * assignee_email and assignee_name: Who solved it
        * resolution_time_hours: How long it took
        * resolution_notes: How it was solved
      - Also provides analysis:
        * most_frequent_assignee: Expert for this type of ticket
        * average_resolution_hours: Expected time to resolve
        * priority_distribution: Common priority levels
      - Use results to make informed assignment decisions
    
    - **get_team_member_by_email**: Retrieves team member details by email address
      - Use this to find assignee information
      - Returns team member profile with skills, role, and availability
    
    - **assign_ticket_with_engine**: Uses sophisticated multi-factor assignment algorithm
      - **Prerequisites**: Must call generate_ticket_embedding and search_similar_tickets FIRST
      - Evaluates ALL team members across 5 scoring dimensions:
        * Similarity: Historical pattern matching (who solved similar tickets)
        * Skills: LLM-based skill extraction and matching
        * Availability: PTO, regional holidays, global holidays (priority-based override)
        * Workload: Contextual calculation (priority × age × status)
        * Timezone: Follow-the-Sun routing (IST/US with overlap windows)
      - Applies business rules:
        * Overload prevention (skips members above 80% capacity)
        * Timezone vs expertise trade-offs (30% score threshold)
        * Fair distribution (limits 5+ assignments per week)
        * Confidence validation (triggers human review if <0.3)
      - Global holiday handling:
        * Critical: 0.5 availability (emergency override)
        * High: 0.3 availability (urgent but reduced)
        * Medium/Low: 0.0 availability (wait until next working day)
      - Returns:
        * assignment_type: "normal", "human_review", or "escalation"
        * primary_assignee: Email of assigned team member
        * confidence_score: 0.0-1.0 confidence in decision
        * reasoning: Detailed explanation of decision factors
        * top_candidates: Top 3 candidates with score breakdowns
      - Automatically updates ticket in database if normal assignment
    
    ## Enhanced Workflow with Assignment Engine:
    1. **Generate Embedding**: Call generate_ticket_embedding() to create vector
    2. **Search Similar Tickets**: Call search_similar_tickets() to find historical patterns
    3. **Run Assignment Engine**: Call assign_ticket_with_engine() for intelligent assignment
    4. **Review Decision**: Examine confidence, reasoning, and top candidates
    5. **Handle Human Review**: If triggered, escalate with provided severity/action
    
    ## Assignment Engine Features:
    - **Logarithmic Similarity Scoring**: Prevents over-favoring frequent assignees
    - **LLM-Based Skill Extraction**: Uses Gemini 2.0 Flash to extract required skills from tickets
    - **Priority-Based Weighting**: Critical prioritizes timezone (35%), Low prioritizes workload (40%)
    - **Cross-Timezone Expertise**: Allows experts to work outside their timezone if >30% better
    - **Workload Context**: Not just ticket count - considers priority, age, and status
    - **N+1 Query Prevention**: Batch fetches all data in 4 optimized queries
    
    ## Guidelines:
    - ALWAYS follow the 3-step workflow: embedding → search → assign
    - Let the assignment engine make the decision (don't override its logic)
    - If confidence < 0.3, respect the human review trigger
    - Present the engine's reasoning and top candidates to the user
    - For human review cases, explain the severity and recommended action
    - Trust the algorithm - it considers factors beyond LLM's immediate context
    
    ## Example Interaction:
    User: "Assign this ticket: AWS S3 access issue for production bucket"
    You:
    1. generate_ticket_embedding(ticket_title="AWS S3 access issue", ...)
    2. search_similar_tickets(top_k=10)
    3. assign_ticket_with_engine()
    4. Report: "Assigned to sarah@company.com with 0.87 confidence. 
       She solved 4/10 similar AWS tickets. Reasoning: High similarity (0.92), 
       strong AWS skills match, IST timezone match, light workload (2 active tickets)."
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,  # Lower temperature for consistent triage decisions
        top_p=0.9,
        top_k=40,
    ),
    tools=[
        generate_ticket_embedding,  # Step 1: Embedding generation for similarity matching
        search_similar_tickets,     # Step 2: Similarity search against historical tickets
        assign_ticket_with_engine,  # Step 3: Intelligent assignment using multi-factor algorithm
        get_team_member_by_email,   # Optional: Team member lookup for additional context
    ],
    output_key="result",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)

__all__ = ["ticket_assignment_agent"]