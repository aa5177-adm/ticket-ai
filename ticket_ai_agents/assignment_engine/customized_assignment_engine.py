"""
Intelligent Ticket Assignment Engine

This module implements a comprehensive, multi-factor assignment algorithm that:
- Learns from historical similar tickets
- Balances workload fairly across team members
- Considers timezone-based routing (India vs US hours)
- Handles edge cases (overload, skills gaps, cross-timezone expertise)
- Provides graduated human-in-loop escalation
- Self-improves through feedback loops
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import math
import pytz

# Import skill extraction tool
from ticket_ai_agents.tools.skills_extraction import extract_skills_from_ticket
from ticket_ai_agents.tools.database_tools import AsyncSessionLocal
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from ticket_ai_agents.models.team_member import TeamMember
from ticket_ai_agents.models.ticket import Ticket
from ticket_ai_agents.models.pto_n_holiday import Holiday, TimeOff, Region
from ticket_ai_agents.models.skills import TeamMemberSkill

@dataclass
class AssignmentCandidate:
    """Represents a potential assignee with all scoring factors"""
    member_id: str
    member_email: str
    member_name: str
    timezone: str
    
    # Score components (0.0 - 1.0)
    similarity_score: float = 0.0
    skill_match_score: float = 0.0
    availability_score: float = 0.0
    workload_score: float = 0.0
    timezone_score: float = 0.0
    
    # Final weighted score
    final_score: float = 0.0
    
    # Supporting data
    solved_similar_count: int = 0
    avg_resolution_hours: Optional[float] = None
    active_tickets_count: int = 0
    recent_assignments_count: int = 0
    weighted_workload: float = 0.0
    
    # Metadata
    notes: List[str] = None
    is_overloaded: bool = False
    has_critical_skills: bool = False

@dataclass
class AssignmentDecision:
    """Final assignment decision with full reasoning"""
    assignment_type: str  # "normal", "human_review", "escalation", "collaborative"
    primary_assignee: Optional[str] = None
    secondary_assignee: Optional[str] = None
    confidence_score: float = 0.0
    
    # All candidates considered
    all_candidates: List[AssignmentCandidate] = None
    
    # Decision reasoning
    reasoning: List[str] = None
    business_rules_applied: List[str] = None
    human_review_triggers: List[Dict[str, str]] = None
    
    # Predictions
    predicted_resolution_hours: Optional[float] = None
    recommended_priority: Optional[str] = None
    
    # Handoff planning
    handoff_plan: Optional[Dict[str, Any]] = None
    collaboration_needed: bool = False
    
    # Metadata
    ticket_id: str = None
    assigned_at: datetime = None
    
    def __post_init__(self):
        if self.all_candidates is None:
            self.all_candidates = []
        if self.reasoning is None:
            self.reasoning = []
        if self.business_rules_applied is None:
            self.business_rules_applied = []
        if self.human_review_triggers is None:
            self.human_review_triggers = []
        if self.assigned_at is None:
            self.assigned_at = datetime.now(timezone.utc)

class AssignmentEngine:
    """
    Core assignment engine that orchestrates the entire assignment process
    """
    # Timezone windows (UTC hours) - Follow-the-Sun with dual handoffs
    IST_START_UTC = 2.5       # 8:00 AM IST
    IST_END_UTC = 14.5        # 8:00 PM IST (extended for overlap)
    
    # Morning Overlap: US→IST Handoff (US ending, IST starting)
    MORNING_OVERLAP_START_UTC = 0.5   # 6:00 AM IST / 8:00 PM EST / 7:00 PM CST
    MORNING_OVERLAP_END_UTC = 2.5     # 8:00 AM IST / 10:00 PM EST / 9:00 PM CST
    
    # Evening Overlap: IST→US Handoff (IST ending, US starting)
    EVENING_OVERLAP_START_UTC = 12.0  # 5:30 PM IST / 8:00 AM EST / 7:00 AM CST
    EVENING_OVERLAP_END_UTC = 14.5    # 8:00 PM IST / 10:30 AM EST / 9:30 AM CST
    
    # Backward compatibility (use evening overlap as main)
    OVERLAP_START_UTC = EVENING_OVERLAP_START_UTC
    OVERLAP_END_UTC = EVENING_OVERLAP_END_UTC

    SIMILARITY_THRESHOLD = 0.70

    def __init__(self):
        """Initialize the assignment engine"""
        self.weight_config = self._load_weight_config()
    
    def _load_weight_config(self) -> Dict[str, Dict[str, float]]:
        """
        Load scoring weights based on ticket priority.
        
        Component Definitions:
        ----------------------
        - similarity: Historical pattern matching (0-1, continuous)
        - skill: Technical expertise match (0-1, continuous)
        - availability: Can they work? PTO/holidays check (0 or 1, BINARY)
        - workload: How busy are they? Active tickets with context (0-1, continuous)
        - timezone: Should they work now? IST/US hours routing (0-1, contextual)
        
        Note: Availability is now BINARY (0=unavailable, 1=available).
        Workload balancing is handled separately in the workload component.
        
        These weights can be adjusted based on feedback.
        """
        return {
            "Critical": {
                "similarity": 0.25,     # High - need expert who solved similar
                "skill": 0.15,          # High - must have critical skills
                "availability": 0.15,   # Medium - binary gate (0 or 1)
                "workload": 0.10,       # Low - ok if busy for Critical
                "timezone": 0.35        # HIGHEST - strict timezone enforcement for urgent issues
            },
            "High": {
                "similarity": 0.25,     # Medium-High - helpful to have experience
                "skill": 0.15,          # High - should have skills
                "availability": 0.15,   # Medium - binary gate (0 or 1)
                "workload": 0.15,       # Medium - consider their load
                "timezone": 0.30        # HIGH - strict timezone enforcement like Critical
            },
            "Medium": {
                "similarity": 0.20,     # Medium - nice to have experience
                "skill": 0.25,          # High - should have skills
                "availability": 0.20,   # Medium - binary gate (0 or 1)
                "workload": 0.20,       # Medium - balance workload
                "timezone": 0.15        # Medium - flexible timing
            },
            "Low": {
                "similarity": 0.15,     # Low - anyone can learn
                "skill": 0.15,          # Low - basic skills ok
                "availability": 0.15,   # Medium - binary gate (0 or 1)
                "workload": 0.40,       # High - prioritize workload balance
                "timezone": 0.15        # Medium - very flexible timing
            }
        }
    
    async def _is_public_holiday(self, region: str, check_date: datetime, session) -> tuple[bool, bool]:
        """
        Check if given date is a public holiday in the specified region.
        Queries from holidays table in database.
        
        Handles both regional holidays (IN/US) and GLOBAL holidays that apply to everyone.
        
        Args:
            region: "India" or "US" 
            check_date: Date to check
            session: Database session to use for query
            
        Returns:
            Tuple of (is_regional_holiday, is_global_holiday)
        """
        # Map region string to Region enum
        region_enum = Region.IN if region == "India" else Region.US
        
        # Query holidays from database - check both regional and GLOBAL
        result = await session.execute(
            select(Holiday).where(
                and_(
                    Holiday.date == check_date.date(),
                    or_(
                        Holiday.region == region_enum,
                        Holiday.region == Region.GLOBAL
                    )
                )
            )
        )
        holidays = result.scalars().all()
        
        # Separate regional and global holidays
        is_regional = any(h.region == region_enum for h in holidays)
        is_global = any(h.region == Region.GLOBAL for h in holidays)
        
        return is_regional, is_global
    
    async def assign_ticket(
        self,
        ticket_details: Dict[str, Any],
        similar_tickets: List[Dict[str, Any]],
        state: Optional[Dict[str, Any]] = None
    ) -> AssignmentDecision:
        """
        Main entry point for ticket assignment.
        
        Args:
            ticket_details: Current ticket information from state
            similar_tickets: Results from search_similar_tickets
            state: Session state (optional, for storing results)
        
        Returns:
            AssignmentDecision with full reasoning
        """
        ticket_id = ticket_details.get("ticket_id", "Unknown")
        ticket_priority = ticket_details.get("priority", "Medium")
        
        # Step 1: Check if human review needed based on similarity
        max_similarity = max(
            (t.get("similarity_score", 0.0) for t in similar_tickets),
            default=0.0
        )
        
        if max_similarity < self.SIMILARITY_THRESHOLD:
            return await self._trigger_human_review(
                ticket_details,
                reason="no_similar_pattern",
                severity="high"
            )
        
        # Step 2: Get all team members and calculate scores
        candidates = await self._evaluate_all_candidates(
            ticket_details,
            similar_tickets,
            ticket_priority
        )
        
        if not candidates:
            return await self._trigger_human_review(
                ticket_details,
                reason="no_available_members",
                severity="critical"
            )
        
        # Step 3: Sort candidates by final score
        candidates.sort(key=lambda x: x.final_score, reverse=True)

        print("*"*30)
        print("Sorted candidates:", candidates)
        print("*"*30)
        
        # Step 4: Apply business rules and make final decision
        decision = await self._apply_business_rules(
            ticket_details,
            candidates,
            similar_tickets
        )
        print("*"*30)
        print("After business rules decision:", decision)
        
        # Step 5: Store decision in state if provided
        if state is not None:
            state["assignment_decision"] = self._decision_to_dict(decision)
        
        return decision

    async def _evaluate_all_candidates(
        self,
        ticket_details: Dict[str, Any],
        similar_tickets: List[Dict[str, Any]],
        ticket_priority: str
    ) -> List[AssignmentCandidate]:
        """
        Evaluate all team members and calculate their assignment scores.
        
        OPTIMIZATION #7: Batch database queries to avoid N+1 problem.
        OPTIMIZATION #8: Extract skills ONCE before evaluating candidates.
        """
        # Get weights for this priority
        weights = self.weight_config.get(ticket_priority, self.weight_config["Medium"])
        
        # OPTIMIZATION #8: Extract skills ONCE and cache for all candidates
        ticket_category = ticket_details.get("category", "")
        ticket_title = ticket_details.get("title", "")
        ticket_description = ticket_details.get("description", "")
        ticket_text = f"Title: {ticket_title}\n\nDescription: {ticket_description}"
        
        print("🔍 Extracting skills from ticket (ONE TIME)...")
        skill_requirements = await extract_skills_from_ticket(
            ticket_text=ticket_text,
            category=ticket_category
        )
        print(f"✓ Skills extracted: {len(skill_requirements.critical_skills)} critical, "
              f"{len(skill_requirements.important_skills)} important, "
              f"{len(skill_requirements.nice_to_have)} nice-to-have")
        
        # OPTIMIZED: Batch fetch all data in minimal queries
        member_data = await self._batch_fetch_member_data()
        
        if not member_data:
            return []
        
        # Evaluate each team member using pre-fetched data AND cached skills
        candidates = []
        for member_id, data in member_data.items():
            candidate = await self._evaluate_candidate_optimized(
                data["member"],
                data["pto_status"],
                data["regional_holiday"],
                data["global_holiday"],
                data["active_tickets_details"],
                data["recent_assignments_count"],
                ticket_details,
                similar_tickets,
                weights,
                skill_requirements  # Pass cached skills
            )
            candidates.append(candidate)

        print("*"*30)
        print(candidates)
        
        return candidates

    async def _batch_fetch_member_data(self) -> Dict[str, Dict[str, Any]]:
        """
        OPTIMIZATION #7: Fetch all member data in minimal queries.
        
        Availability now only checks PTO and holidays (not workload).
        Workload calculations still need active ticket details.
        
        Returns:
            Dict mapping member_id to {
                member, pto_status, regional_holiday, active_tickets_details
            }
        """
        async with AsyncSessionLocal() as session:
            # Query 1: Get all team members with their skills eagerly loaded
            members_result = await session.execute(
                select(TeamMember)
                .options(selectinload(TeamMember.skills).selectinload(TeamMemberSkill.skill))
                .where(TeamMember.app_role.in_(["USER"]))
            )
            team_members = members_result.scalars().all()
            
            if not team_members:
                return {}
            
            member_ids = [m.id for m in team_members]
            print(member_ids)
            current_date = datetime.now(timezone.utc)
            
            # Query 2: Get all active ticket details for workload calculation
            active_tickets_result = await session.execute(
                select(Ticket)
                .where(
                    and_(
                        Ticket.assignee_id.in_(member_ids),
                        Ticket.status.in_(["OPEN", "IN_PROGRESS", "PENDING"])
                    )
                )
            )
            all_active_tickets = active_tickets_result.scalars().all()
            
            # Group tickets by assignee
            tickets_by_member = {}
            for ticket in all_active_tickets:
                if ticket.assignee_id not in tickets_by_member:
                    tickets_by_member[ticket.assignee_id] = []
                tickets_by_member[ticket.assignee_id].append(ticket)
            print("*"*30)
            print(tickets_by_member)
            
            # Query 3: Get all active time-offs (PTO) for all members
            time_offs_result = await session.execute(
                select(TimeOff)
                .where(
                    and_(
                        TimeOff.member_id.in_(member_ids),
                        TimeOff.start_date <= current_date.date(),
                        TimeOff.end_date >= current_date.date()
                    )
                )
            )
            all_time_offs = time_offs_result.scalars().all()
            print("*"*30)
            print(all_time_offs)
            # Create set of member IDs on PTO
            members_on_pto = {str(to.member_id) for to in all_time_offs}
            
            # Query 4: Get recent assignments (last 7 days) for fair distribution
            seven_days_ago = current_date - timedelta(days=7)
            recent_assignments_result = await session.execute(
                select(Ticket.assignee_id, func.count(Ticket.id).label('assignment_count'))
                .where(
                    and_(
                        Ticket.assignee_id.in_(member_ids),
                        Ticket.created_at >= seven_days_ago,
                        Ticket.created_at.isnot(None)
                    )
                )
                .group_by(Ticket.assignee_id)
            )
            recent_assignments_data = recent_assignments_result.all()
            
            # Create dict mapping member_id to recent assignment count
            recent_assignments_by_member = {
                str(row.assignee_id): row.assignment_count 
                for row in recent_assignments_data
            }
            print("*"*30)
            print(f"Recent assignments (last 7 days): {recent_assignments_by_member}")
            
            # Build result dictionary
            member_data = {}
            
            for member in team_members:
                # Determine member's region from timezone
                member_region = "India" if "Asia/" in (member.timezone or "") else "US"
                
                # Check holiday status from database (returns tuple: regional, global)
                is_regional_holiday, is_global_holiday = await self._is_public_holiday(member_region, current_date, session)
                
                # Check PTO status from database query
                is_on_pto = str(member.id) in members_on_pto
                
                member_data[str(member.id)] = {
                    "member": member,
                    "pto_status": is_on_pto,
                    "regional_holiday": is_regional_holiday,
                    "global_holiday": is_global_holiday,
                    "active_tickets_details": tickets_by_member.get(member.id, []),
                    "recent_assignments_count": recent_assignments_by_member.get(str(member.id), 0)
                }
            
            return member_data

    async def _evaluate_candidate_optimized(
        self,
        member: TeamMember,
        pto_status: bool,
        regional_holiday: bool,
        global_holiday: bool,
        active_tickets_details: List[Ticket],
        recent_assignments_count: int,
        ticket_details: Dict[str, Any],
        similar_tickets: List[Dict[str, Any]],
        weights: Dict[str, float],
        skill_requirements: Any  # Pre-extracted skills (from _evaluate_all_candidates)
    ) -> AssignmentCandidate:
        """
        OPTIMIZATION #7: Evaluate candidate using pre-fetched batch data.
        OPTIMIZATION #8: Use pre-extracted skills instead of extracting per candidate.
        
        Availability is now PURE binary check (PTO/holidays only).
        Workload still uses contextual calculation with ticket details.
        """
        candidate = AssignmentCandidate(
            member_id=str(member.id),
            member_email=member.email,
            member_name=member.name,
            timezone=member.timezone or "UTC"
        )
        
        # Calculate each component score
        candidate.similarity_score = self._calculate_similarity_score(
            member,
            similar_tickets
        )
        
        # Use cached skill requirements instead of extracting again
        candidate.skill_match_score = self._calculate_skill_match_score_cached(
            member,
            skill_requirements
        )
        
        # REFINED: Availability with smart global holiday handling
        ticket_priority = ticket_details.get("priority", "Medium")
        availability_data = self._calculate_availability_score_optimized(
            pto_status,
            regional_holiday,
            global_holiday,
            ticket_priority
        )
        candidate.availability_score = availability_data["score"]
        candidate.is_overloaded = False  # Not determined by availability anymore
        
        # Store holiday context in notes for transparency
        if availability_data.get("reason"):
            if candidate.notes is None:
                candidate.notes = []
            candidate.notes.append(availability_data["reason"])
        
        # OPTIMIZED: Workload uses pre-fetched ticket details
        workload_data = self._calculate_workload_score_optimized(
            active_tickets_details
        )
        candidate.workload_score = workload_data["score"]
        candidate.weighted_workload = workload_data["weighted_workload"]
        candidate.active_tickets_count = len(active_tickets_details)
        candidate.is_overloaded = workload_data.get("is_overloaded", False)
        
        # Store recent assignments count for fair distribution
        candidate.recent_assignments_count = recent_assignments_count
        
        # Timezone scoring (unchanged)
        candidate.timezone_score = self._calculate_timezone_score(
            member,
            ticket_details,
            candidate.solved_similar_count
        )
        
        # Calculate final weighted score
        candidate.final_score = (
            candidate.similarity_score * weights["similarity"] +
            candidate.skill_match_score * weights["skill"] +
            candidate.availability_score * weights["availability"] +
            candidate.workload_score * weights["workload"] +
            candidate.timezone_score * weights["timezone"]
        )
        
        return candidate
    
    def _calculate_similarity_score(
        self,
        member: TeamMember,
        similar_tickets: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate similarity score with logarithmic scaling to avoid over-favoring
        frequent assignees.
        
        Improvements:
        - Logarithmic scaling for solved_count (diminishing returns)
        - Recency weighting (recent experience valued higher)
        - Average similarity of their specific tickets
        """
        # Filter similar tickets solved by this member
        member_similar = [
            t for t in similar_tickets
            if t.get("assignee_email") == member.email
        ]
        
        if not member_similar:
            return 0.0
        
        solved_count = len(member_similar)
        
        # Logarithmic scaling: log(n+1) / log(6)
        # This gives: 1 ticket=0.39, 2=0.58, 3=0.69, 5=0.90, 10=1.0
        expertise_factor = math.log(solved_count + 1) / math.log(6)
        expertise_factor = min(expertise_factor, 1.0)
        
        # Average similarity score of tickets they solved
        avg_similarity = sum(t["similarity_score"] for t in member_similar) / len(member_similar)
        
        # Check if they solved similar tickets recently (within 30 days)
        # Note: In production, you'd parse resolved_at dates
        # recent_weight = 0.7  # Assume some recency bonus for now
        
        # Final similarity score
        similarity_score = (
            expertise_factor * 0.3 +
            avg_similarity * 0.7 
            # recent_weight * 0.2
        )
        
        # Store metadata
        # candidate.solved_similar_count = solved_count
        # candidate.avg_resolution_hours = calculate_avg_resolution(member_similar)
        
        return min(similarity_score, 1.0)
    
    def _calculate_skill_match_score_cached(
        self,
        member: TeamMember,
        skill_requirements: Any
    ) -> float:
        """
        Calculate skill match score using PRE-EXTRACTED skills.
        
        OPTIMIZATION #8: This method receives already-extracted skills,
        avoiding duplicate LLM calls for each candidate.
        
        Args:
            member: Team member to evaluate
            skill_requirements: Pre-extracted SkillRequirements object
        
        Returns:
            Float score between 0.0 and 1.0 indicating skill match quality
        """
        # Extract categorized skills from Pydantic model
        critical_skills = skill_requirements.critical_skills
        important_skills = skill_requirements.important_skills
        nice_to_have = skill_requirements.nice_to_have
        
        # Get member's skills from database (via relationship)
        member_skills = self._get_member_skills(member)
        
        # Calculate match scores
        critical_match = sum(
            1.0 for skill in critical_skills
            if skill in member_skills
        ) / max(len(critical_skills), 1)
        
        # If missing critical skills, heavily penalize
        if critical_match < 0.5 and critical_skills:
            return 0.2  # Low score, likely not suitable
        
        important_match = sum(
            1.0 for skill in important_skills
            if skill in member_skills
        ) / max(len(important_skills), 1) if important_skills else 0.5
        
        nice_match = sum(
            1.0 for skill in nice_to_have
            if skill in member_skills
        ) / max(len(nice_to_have), 1) if nice_to_have else 0.5
        
        # Weighted calculation
        skill_match_score = (
            critical_match * 0.6 +
            important_match * 0.3 +
            nice_match * 0.1
        )
        
        # Bonus for recent experience (placeholder - would query recent tickets)
        # skill_match_score *= 1.15 if has_recent_experience else 1.0
        
        # Bonus for certifications (placeholder - would check certifications table)
        # skill_match_score *= 1.10 if has_certification else 1.0
        
        return min(skill_match_score, 1.0)
    
    def _get_member_skills(self, member: TeamMember) -> List[str]:
        """
        Get member skills from their profile.
        
        Uses the relationship already loaded with the member object.
        The member.skills relationship contains TeamMemberSkill objects,
        each with a skill relationship to the Skill object.
        
        Returns:
            List of lowercase skill names
        """
        if not member.skills:
            # Fallback: Default skills for all engineers if no skills in database
            return ["troubleshooting", "documentation"]
        
        # Extract skill names from the relationship
        # member.skills -> List[TeamMemberSkill]
        # member_skill.skill -> Skill object
        # skill.name -> skill name string
        skills = [
            member_skill.skill.name.lower().strip()
            for member_skill in member.skills
            if member_skill.skill and member_skill.skill.name
        ]
        
        # Deduplicate while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            if skill not in seen:
                seen.add(skill)
                unique_skills.append(skill)
        
        return unique_skills if unique_skills else ["troubleshooting", "documentation"]

    def _calculate_availability_score_optimized(
            self,
            pto_status: bool,
            regional_holiday: bool,
            global_holiday: bool,
            ticket_priority: str
        ) -> Dict[str, Any]:
            """
            REFINED: Availability check with smart global holiday handling.
            
            Hard blockers (always 0.0):
            - Personal PTO/TimeOff
            - Regional holidays
            
            Soft blockers (priority-based override for global holidays):
            - Global holidays: 0.0 for Low/Medium, 0.3 for High, 0.5 for Critical
            
            This allows Critical incidents to be handled even on global holidays
            while protecting team wellbeing for routine work.
            
            Args:
                pto_status: Is member on PTO/TimeOff?
                regional_holiday: Is it a public holiday in their region?
                global_holiday: Is it a global holiday (applies to everyone)?
                ticket_priority: Priority of the ticket (Critical/High/Medium/Low)
                
            Returns:
                Dict with score (0.0-1.0), available flag, and reason
            """
            # Hard blockers - cannot work at all
            if pto_status:
                return {
                    "score": 0.0,
                    "available": False,
                    "reason": "On PTO/TimeOff",
                    "is_overloaded": False  # Not overloaded, just unavailable
                }
            
            if regional_holiday:
                return {
                    "score": 0.0,
                    "available": False,
                    "reason": "Regional public holiday",
                    "is_overloaded": False
                }
            
            # Soft blocker - global holiday with priority-based override
            if global_holiday:
                # Priority-based availability during global holidays
                priority_override = {
                    "Critical": 0.5,  # Allow assignment with penalty (emergency override)
                    "High": 0.3,      # Reduced availability (urgent but can wait)
                    "Medium": 0.0,    # Block assignment (can wait until next working day)
                    "Low": 0.0        # Block assignment (definitely can wait)
                }
                score = priority_override.get(ticket_priority, 0.0)
                
                if score > 0.0:
                    return {
                        "score": score,
                        "available": True,
                        "reason": f"Global holiday (emergency override for {ticket_priority} priority)",
                        "is_overloaded": False
                    }
                else:
                    return {
                        "score": 0.0,
                        "available": False,
                        "reason": f"Global holiday ({ticket_priority} priority can wait)",
                        "is_overloaded": False
                    }
            
            # Future: Add more hard blockers
            # - Sick leave
            # - Bereavement leave
            # - Training/conference
            
            # Fully available to work
            return {
                "score": 1.0,
                "available": True,
                "reason": "Available",
                "is_overloaded": False
            }
    
    def _calculate_workload_score_optimized(
        self,
        active_tickets: List[Ticket]
    ) -> Dict[str, Any]:
        """
        OPTIMIZATION #7: Calculate workload using pre-fetched ticket details.
        
        This handles "How busy are they?" with contextual factors:
        - Priority (Critical counts more)
        - Age (Stuck tickets count more)
        - Status (Blocked tickets count less)
        - Complexity estimates
        
        Returns continuous score: 0.0 (overloaded) to 1.0 (free)
        
        Args:
            active_tickets: List of active tickets for this member
        """
        if not active_tickets:
            return {
                "score": 1.0,
                "weighted_workload": 0.0,
                "is_overloaded": False
            }
        
        effective_workload = 0.0
        
        for ticket in active_tickets:
            # Priority weight
            priority_weights = {
                "Critical": 3.0,
                "High": 2.0,
                "Medium": 1.0,
                "Low": 0.5
            }
            priority_weight = priority_weights.get(ticket.priority, 1.0)
            
            # Age factor (stuck tickets are problematic)
            # Use timezone-aware datetime to match ticket.created_at
            current_time = datetime.now(timezone.utc)
            ticket_age = (current_time - ticket.created_at).days
            if ticket_age > 7:
                age_penalty = 1.5  # Stuck tickets count more
            elif ticket_age > 3:
                age_penalty = 1.2
            else:
                age_penalty = 1.0
            
            # Status factor (blocked/waiting tickets less active burden)
            if ticket.status in ["Blocked", "Waiting"]:
                status_weight = 0.3  # Less burden
            elif ticket.status == "In Progress":
                status_weight = 1.0  # Full burden
            else:  # "Open"
                status_weight = 0.5  # Medium burden
            
            # Complexity (placeholder - would use story points or estimates)
            complexity_factor = 1.0
            
            # Calculate effective load for this ticket
            ticket_load = (
                priority_weight *
                age_penalty *
                status_weight *
                complexity_factor
            )
            
            effective_workload += ticket_load
        
        # Calculate workload score (inverse - lower load = higher score)
        team_max_load = 30.0  # Maximum capacity
        workload_score = max(0, 1.0 - (effective_workload / team_max_load))
        
        # Check if overloaded
        is_overloaded = effective_workload >= team_max_load * 0.8  # 80% capacity
        
        # Efficiency bonus (placeholder - would calculate from resolution history)
        # if member.avg_resolution_time < team_avg:
        #     workload_score *= 1.1  # Fast resolvers can handle slightly more
        
        return {
            "score": min(workload_score, 1.0),
            "weighted_workload": effective_workload,
            "is_overloaded": is_overloaded,
            "active_ticket_count": len(active_tickets)
        }   

    def _calculate_timezone_score(
        self,
        member: TeamMember,
        ticket_details: Dict[str, Any],
        solved_similar_count: int
    ) -> float:
        """
        Calculate BALANCED timezone score that is fair to both IST and US teams.
        
        Approach:
        - 3 time windows: IST-preferred, OVERLAP (both ok), US-preferred
        - Reduced penalties: 0.5 instead of 0.2 for wrong timezone
        - Overlap window: Both teams get good scores (0.85-1.0)
        - Expertise boost: Experts can work cross-timezone
        - Critical urgency: Timezone matters less
        
        Score ranges:
        - 1.0: Perfect match (in working hours)
        - 0.85: Overlap window (both teams can work)
        - 0.6: Expert in wrong timezone
        - 0.5: Wrong timezone but flexible (not blocking)
        """
        # Get current time in UTC
        current_utc = datetime.now(timezone.utc)
        current_hour_utc = current_utc.hour + current_utc.minute / 60.0
        
        # Determine member timezone
        member_tz = member.timezone or "UTC"
        is_ist = "Asia/Kolkata" in member_tz or "Asia/Calcutta" in member_tz or "Asia/" in member_tz
        is_us = "America/" in member_tz or "US/" in member_tz
        
        # Determine time window and calculate base score (Follow-the-Sun with dual handoffs)
        if self.MORNING_OVERLAP_START_UTC <= current_hour_utc < self.MORNING_OVERLAP_END_UTC:
            # MORNING OVERLAP (0.5-2.5 UTC): US→IST Handoff
            # 6:00 AM - 8:00 AM IST (IST starting day)
            # 8:00 PM - 10:00 PM EST / 7:00 PM - 9:00 PM CST (US ending day)
            time_window = "MORNING_OVERLAP"
            if is_ist:
                timezone_score = 0.85  # Good for IST (early morning, starting day)
            elif is_us:
                timezone_score = 1.0   # Perfect for US (wrapping up day)
            else:
                timezone_score = 0.6
                
        elif self.EVENING_OVERLAP_START_UTC <= current_hour_utc < self.EVENING_OVERLAP_END_UTC:
            # EVENING OVERLAP (12.0-14.5 UTC): IST→US Handoff
            # 5:30 PM - 8:00 PM IST (IST ending day)
            # 8:00 AM - 10:30 AM EST / 7:00 AM - 9:30 AM CST (US starting day)
            time_window = "EVENING_OVERLAP"
            if is_ist:
                timezone_score = 1.0   # Perfect for IST (wrapping up day)
            elif is_us:
                timezone_score = 0.85  # Good for US (early morning, starting day)
            else:
                timezone_score = 0.6
                
        elif self.IST_START_UTC <= current_hour_utc < self.EVENING_OVERLAP_START_UTC:
            # IST-ONLY WINDOW (2.5-12.0 UTC): IST core working hours
            # 8:00 AM - 5:30 PM IST (full IST work day)
            # 10:30 PM - 8:00 AM EST (night/early morning for US)
            time_window = "IST_ONLY"
            if is_ist:
                timezone_score = 1.0   # Perfect for IST
            elif is_us:
                timezone_score = 0.5   # US can help but not ideal (night/early morning)
            else:
                timezone_score = 0.4
                
        else:
            # US-ONLY WINDOW (14.5-0.5 UTC): US core working hours
            # 10:30 AM - 6:00 PM EST / 9:30 AM - 5:00 PM CST (full US work day)
            # 8:00 PM - 6:00 AM IST (evening/night for IST)
            time_window = "US_ONLY"
            if is_us:
                timezone_score = 1.0   # Perfect for US
            elif is_ist:
                timezone_score = 0.5   # IST can help but not ideal (evening/night)
            else:
                timezone_score = 0.4
        
        # CRITICAL & HIGH TICKETS: Strict timezone enforcement
        # For Critical/High priority, timezone matters MORE - reduce wrong-timezone scores
        # Medium/Low priorities: Flexible ONLY in overlap window
        priority = ticket_details.get("priority")
        
        if priority in ["Critical", "High"]:
            if timezone_score == 0.5:  # Wrong timezone
                timezone_score = 0.3  # Reduced score (strict enforcement)
            elif timezone_score == 0.4:  # Other timezone
                timezone_score = 0.2  # Very low score
            # Only exception: Experts in overlap window still get good score
            # This ensures Critical/High tickets go to correct timezone team
        
        # CROSS-TIMEZONE EXPERTISE: Experts get boost based on priority AND time window
        # Critical/High: Limited cross-timezone (timezone still matters)
        # Medium/Low: Cross-timezone flexibility ONLY in overlap windows (reasonable hours)
        if solved_similar_count >= 3:
            if priority in ["Medium", "Low"]:
                # Check if we're in either overlap window (morning or evening handoff)
                in_morning_overlap = (self.MORNING_OVERLAP_START_UTC <= current_hour_utc < self.MORNING_OVERLAP_END_UTC)
                in_evening_overlap = (self.EVENING_OVERLAP_START_UTC <= current_hour_utc < self.EVENING_OVERLAP_END_UTC)
                
                if in_morning_overlap or in_evening_overlap:
                    # OVERLAP WINDOW: Expert can work cross-timezone (both teams available)
                    # Morning: 6:00-8:00 AM IST / 7:00-10:00 PM CST-EST (US→IST handoff)
                    # Evening: 5:30-8:00 PM IST / 7:00-10:30 AM CST-EST (IST→US handoff)
                    if timezone_score < 0.85:
                        timezone_score = 0.85  # Good score in overlap
                elif timezone_score >= 0.75:
                    # Already in correct timezone (1.0 or 0.85), keep it
                    pass
                else:
                    # OUTSIDE OVERLAP: Wrong timezone expert at extreme hours
                    # Example: US expert at 3 AM UTC (8:30 AM IST, 10 PM EST previous day)
                    # Example: IST expert at 18 PM UTC (11:30 PM IST, 1 PM EST)
                    # Don't boost - let them rest!
                    timezone_score = 0.4  # Low score (not available at extreme hours)
                    
            elif priority in ["Critical", "High"]:
                # Critical/High: Expert boost is smaller (timezone still matters)
                if timezone_score < 0.6 and timezone_score >= 0.3:
                    timezone_score = 0.6  # Moderate boost for urgent tickets
                # Note: Wrong timezone (0.3) stays low even for experts
        
        return timezone_score    
    
    def _get_preferred_timezone(self) -> str:
        """Determine current preferred timezone"""
        current_utc = datetime.now(pytz.UTC)
        current_hour_utc = current_utc.hour + current_utc.minute / 60.0
        
        if self.IST_START_UTC <= current_hour_utc <= self.IST_END_UTC:
            return "IST"
        else:
            return "US"
    
    def _check_timezone_match(self, candidate: AssignmentCandidate, preferred: str) -> bool:
        """Check if candidate timezone matches preferred"""
        is_ist = "Asia/" in candidate.timezone
        is_us = "America/" in candidate.timezone or "US/" in candidate.timezone
        
        if preferred == "IST":
            return is_ist
        elif preferred == "US":
            return is_us
        return False
    
    async def _apply_business_rules(
        self,
        ticket_details: Dict[str, Any],
        candidates: List[AssignmentCandidate],
        similar_tickets: List[Dict[str, Any]]
    ) -> AssignmentDecision:
        """
        Apply business rules and edge case handling to make final decision.
        
        Rules:
        1. Overload prevention
        2. Timezone mismatch resolution
        3. Fair distribution override
        4. Skills gap detection
        5. Collaboration detection
        6. Handoff planning
        7. Confidence-based validation
        """
        decision = AssignmentDecision(
            assignment_type="normal",  # Will be updated based on business rules
            ticket_id=ticket_details.get("ticket_id"),
            all_candidates=candidates
        )
        
        top_candidate = candidates[0]

        # Rule 1: Check if top candidate is overloaded
        if top_candidate.is_overloaded or top_candidate.workload_score < 0.3:
            decision.business_rules_applied.append("overload_prevention")
            
            # Find next available candidate (not overloaded and actually available)
            available = [
                c for c in candidates 
                if not c.is_overloaded and c.availability_score > 0.0 and c.workload_score >= 0.5
            ]
            
            if available:
                top_candidate = available[0]
                decision.reasoning.append(
                    f"Top choice ({candidates[0].member_name}) is overloaded. "
                    f"Assigned to next available: {top_candidate.member_name}"
                )
            else:
                # Everyone overloaded - escalate
                return await self._trigger_human_review(
                    ticket_details,
                    reason="team_at_capacity",
                    severity="critical"
                )
        
        # Rule 2: Timezone mismatch for expert ??
        preferred_tz = self._get_preferred_timezone()
        top_tz_matches = self._check_timezone_match(top_candidate, preferred_tz)
        
        if not top_tz_matches and top_candidate.similarity_score > 0.7:
            decision.business_rules_applied.append("timezone_vs_expertise")
            
            # Find best in-timezone candidate
            in_tz_candidates = [
                c for c in candidates
                if self._check_timezone_match(c, preferred_tz)
            ]
            
            if in_tz_candidates:
                best_in_tz = in_tz_candidates[0]
                score_diff = top_candidate.final_score - best_in_tz.final_score
                
                if score_diff > 0.30:
                    # Expert significantly better 30%
                    decision.reasoning.append(
                        f"Cross-timezone assignment: {top_candidate.member_name} is expert "
                        f"(solved {top_candidate.solved_similar_count} similar tickets)"
                    )
                else:
                    # Scores close, prefer in-timezone
                    top_candidate = best_in_tz
                    decision.reasoning.append(
                        "Preferred in-timezone member with comparable skills"
                    )
            
        # Rule 3: Fair distribution - prevent same person getting too many recent assignments
        # Check if top candidate has been assigned too many tickets in last 7 days
        if top_candidate.recent_assignments_count >= 5:  # 5+ assignments in last 7 days
            decision.business_rules_applied.append("fair_distribution")
            
            # Find less-loaded alternatives in top 5 candidates
            less_loaded = [
                c for c in candidates[1:5]
                if c.recent_assignments_count < 5 and c.availability_score > 0.0
            ]
            
            if less_loaded:
                old_top = top_candidate
                top_candidate = less_loaded[0]
                decision.reasoning.append(
                    f"{old_top.member_name} has {old_top.recent_assignments_count} assignments in last 7 days. "
                    f"Fair distribution to {top_candidate.member_name} ({top_candidate.recent_assignments_count} recent assignments)"
                )

        # Rule 4: Skills gap detection
        if top_candidate.skill_match_score < 0.25:
            decision.business_rules_applied.append("skills_gap_detected")
            decision.reasoning.append(
                "Skills gap detected - no team member is strong match. "
                "Consider external consultation or training."
            )
            # Continue with assignment but flag it
        
        # Rule 5: Collaboration needed?
        # if self._needs_collaboration(ticket_details, similar_tickets):
        #     decision.collaboration_needed = True
        #     decision.business_rules_applied.append("collaborative_assignment")
            
        #     # Find complementary secondary assignee
        #     secondary = self._find_secondary_assignee(candidates, top_candidate)
        #     if secondary:
        #         decision.secondary_assignee = secondary.member_email
        #         decision.reasoning.append(
        #             f"Collaborative assignment: Primary={top_candidate.member_name}, "
        #             f"Secondary={secondary.member_name}"
        #         )
        
        # Rule 6: Handoff planning for multi-day tickets
        # predicted_hours = self._estimate_resolution_time(similar_tickets)
        # if predicted_hours and predicted_hours > 8:
        #     handoff = self._plan_handoff(top_candidate, candidates)
        #     if handoff:
        #         decision.handoff_plan = handoff
        #         decision.business_rules_applied.append("follow_the_sun_handoff")
        
        # Rule 7: Confidence-based validation
        confidence = self._calculate_confidence(top_candidate, candidates)
        decision.confidence_score = confidence
        
        if confidence < 0.3:
            return await self._trigger_human_review(
                ticket_details,
                reason="low_confidence_assignment",
                severity="medium"
            )
        elif confidence < 0.5:
            decision.reasoning.append(
                "Medium confidence assignment - team lead notified"
            )
            decision.business_rules_applied.append("team_lead_notification")
        
        # Final assignment
        decision.assignment_type = "collaborative" if decision.collaboration_needed else "normal"
        decision.primary_assignee = top_candidate.member_email
        # decision.predicted_resolution_hours = predicted_hours
        
        # Add final reasoning
        decision.reasoning.append(
            f"Assigned to {top_candidate.member_name}: "
            f"Score={top_candidate.final_score:.2f} "
            f"(Similarity={top_candidate.similarity_score:.2f}, "
            f"Skills={top_candidate.skill_match_score:.2f}, "
            f"Availability={top_candidate.availability_score:.2f})"
        )
        print("*"*30)
        print(decision)
        return decision        
    
    def _calculate_confidence(
        self,
        top_candidate: AssignmentCandidate,
        all_candidates: List[AssignmentCandidate]
    ) -> float:
        """Calculate confidence in the assignment decision"""
        confidence_factors = {
            "high_similarity": top_candidate.similarity_score > 0.70,
            "strong_skills": top_candidate.skill_match_score > 0.5,
            "good_availability": top_candidate.availability_score > 0.7,
            "clear_winner": (
                len(all_candidates) > 1 and
                (top_candidate.final_score - all_candidates[1].final_score) > 0.15
            ),
            "timezone_match": top_candidate.timezone_score >= 1.0
        }
        # confidence_factors = {
        #     "high_similarity": top_candidate.similarity_score > 0.85,
        #     "strong_skills": top_candidate.skill_match_score > 0.8,
        #     "good_availability": top_candidate.availability_score > 0.7,
        #     "clear_winner": (
        #         len(all_candidates) > 1 and
        #         (top_candidate.final_score - all_candidates[1].final_score) > 0.15
        #     ),
        #     "timezone_match": top_candidate.timezone_score >= 1.0
        # }
        
        confidence_score = sum(confidence_factors.values()) / len(confidence_factors)
        return confidence_score
    
    async def _trigger_human_review(
        self,
        ticket_details: Dict[str, Any],
        reason: str,
        severity: str
    ) -> AssignmentDecision:
        """
        Trigger human-in-loop review with appropriate escalation level.
        
        Severity levels:
        - critical: Immediate manager escalation
        - high: Team email, 1 hour timeout
        - medium: Team lead review
        - low: Assign with note
        """
        decision = AssignmentDecision(
            ticket_id=ticket_details.get("ticket_id"),
            assignment_type="human_review"
        )
        
        trigger = {
            "reason": reason,
            "severity": severity,
            "ticket_id": ticket_details.get("ticket_id"),
            "ticket_title": ticket_details.get("title")
        }
        
        if severity == "critical":
            trigger["action"] = "immediate_manager_escalation"
            trigger["message"] = "Team at capacity or critical issue requires immediate attention"
        elif severity == "high":
            trigger["action"] = "team_consultation_email"
            trigger["timeout"] = "1 hour"
            trigger["message"] = "No similar pattern found - team input needed"
        elif severity == "medium":
            trigger["action"] = "team_lead_review"
            trigger["timeout"] = "15 minutes"
            trigger["message"] = "Low confidence assignment - team lead review requested"
        
        decision.human_review_triggers.append(trigger)
        decision.reasoning.append(f"Human review triggered: {reason} (severity: {severity})")
        
        return decision
    
    def _decision_to_dict(self, decision: AssignmentDecision) -> Dict[str, Any]:
        """Convert AssignmentDecision to dictionary for state storage"""
        return {
            "assignment_type": decision.assignment_type,
            "primary_assignee": decision.primary_assignee,
            "secondary_assignee": decision.secondary_assignee,
            "confidence_score": decision.confidence_score,
            "reasoning": decision.reasoning,
            "business_rules_applied": decision.business_rules_applied,
            "human_review_triggers": decision.human_review_triggers,
            "predicted_resolution_hours": decision.predicted_resolution_hours,
            # "handoff_plan": decision.handoff_plan,
            # "collaboration_needed": decision.collaboration_needed,
            "assigned_at": decision.assigned_at.isoformat(),
            "candidates_count": len(decision.all_candidates),
            "top_3_candidates": [
                {
                    "name": c.member_name,
                    "email": c.member_email,
                    "score": round(c.final_score, 3),
                    "breakdown": {
                        "similarity": round(c.similarity_score, 2),
                        "skill": round(c.skill_match_score, 2),
                        "availability": round(c.availability_score, 2),
                        "workload": round(c.workload_score, 2),
                        "timezone": round(c.timezone_score, 2)
                    }
                }
                for c in decision.all_candidates[:3]
            ]
        }
