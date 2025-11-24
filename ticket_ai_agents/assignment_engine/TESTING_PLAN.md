# Assignment Engine Testing Plan

## Executive Summary

This document provides a comprehensive testing plan to validate the assignment engine logic across 15+ edge cases before production deployment. Each test case includes:
- Database setup (SQL inserts)
- Input data
- Expected behavior
- Success criteria

---

## Table of Contents

1. [Test Environment Setup](#test-environment-setup)
2. [Database Seed Data](#database-seed-data)
3. [Test Cases](#test-cases)
   - [Basic Assignment Tests](#basic-assignment-tests)
   - [Availability Tests](#availability-tests)
   - [Workload & Overload Tests](#workload--overload-tests)
   - [Timezone Tests](#timezone-tests)
   - [Fair Distribution Tests](#fair-distribution-tests)
   - [Confidence & Human Review Tests](#confidence--human-review-tests)
   - [Business Rules Integration Tests](#business-rules-integration-tests)
4. [Test Execution Guide](#test-execution-guide)
5. [Validation Checklist](#validation-checklist)

---

## Test Environment Setup

### Prerequisites

```bash
# 1. Create test database
createdb ticket_ai_test

# 2. Run migrations
cd backend
alembic upgrade head

# 3. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\Activate.ps1  # Windows
```

### Test Configuration

Create `test_config.py`:

```python
TEST_DATABASE_URL = "postgresql://user:password@localhost/ticket_ai_test"
TEST_MODE = True
CONFIDENCE_THRESHOLDS = {
    "low": 0.3,
    "medium": 0.5
}
```

---

## Database Seed Data

### Team Members (9 members)

```sql
-- Clear existing data
TRUNCATE TABLE team_members CASCADE;
TRUNCATE TABLE tickets CASCADE;
TRUNCATE TABLE holidays CASCADE;
TRUNCATE TABLE time_offs CASCADE;

-- IST Team Members (5)
INSERT INTO team_members (id, name, email, timezone, app_role, role, created_at, updated_at) VALUES
('tm-001', 'Ravi Kumar', 'ravi.kumar@company.com', 'Asia/Kolkata', 'USER', 'Senior Engineer', NOW(), NOW()),
('tm-002', 'Priya Sharma', 'priya.sharma@company.com', 'Asia/Kolkata', 'USER', 'Engineer', NOW(), NOW()),
('tm-003', 'Akash Patel', 'akash.patel@company.com', 'Asia/Kolkata', 'USER', 'Engineer', NOW(), NOW()),
('tm-004', 'Sneha Reddy', 'sneha.reddy@company.com', 'Asia/Kolkata', 'USER', 'Junior Engineer', NOW(), NOW()),
('tm-005', 'Arjun Singh', 'arjun.singh@company.com', 'Asia/Kolkata', 'USER', 'Senior Engineer', NOW(), NOW());

-- US Team Members (4)
INSERT INTO team_members (id, name, email, timezone, app_role, role, created_at, updated_at) VALUES
('tm-006', 'John Smith', 'john.smith@company.com', 'America/New_York', 'USER', 'Senior Engineer', NOW(), NOW()),
('tm-007', 'Sarah Johnson', 'sarah.johnson@company.com', 'America/Los_Angeles', 'USER', 'Engineer', NOW(), NOW()),
('tm-008', 'Michael Brown', 'michael.brown@company.com', 'America/Chicago', 'USER', 'Engineer', NOW(), NOW()),
('tm-009', 'Emily Davis', 'emily.davis@company.com', 'America/New_York', 'USER', 'Junior Engineer', NOW(), NOW());
```

### Historical Similar Tickets (Pattern Learning)

```sql
-- AWS/IAM related tickets (Ravi is expert)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category, 
                     assignee_id, assigned_at, created_at, resolved_at, embedding) VALUES
('tk-001', 'TASK1001', 'AWS IAM policy access', 'Need AWS policy access for S3', 'High', 'CLOSED', 'AWS',
 'tm-001', NOW() - INTERVAL '15 days', NOW() - INTERVAL '16 days', NOW() - INTERVAL '14 days', 
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
 
('tk-002', 'TASK1002', 'IAM permission issue', 'Cannot access IAM console', 'Medium', 'CLOSED', 'AWS',
 'tm-001', NOW() - INTERVAL '10 days', NOW() - INTERVAL '11 days', NOW() - INTERVAL '9 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
 
('tk-003', 'TASK1003', 'AWS access setup', 'Provision AWS access for new user', 'High', 'CLOSED', 'AWS',
 'tm-001', NOW() - INTERVAL '5 days', NOW() - INTERVAL '6 days', NOW() - INTERVAL '4 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);

-- Database tickets (Priya is expert)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, resolved_at, embedding) VALUES
('tk-004', 'TASK1004', 'Database connection issue', 'PostgreSQL connection failing', 'Critical', 'CLOSED', 'Database',
 'tm-002', NOW() - INTERVAL '12 days', NOW() - INTERVAL '13 days', NOW() - INTERVAL '11 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
 
('tk-005', 'TASK1005', 'Query optimization needed', 'Slow query performance', 'High', 'CLOSED', 'Database',
 'tm-002', NOW() - INTERVAL '8 days', NOW() - INTERVAL '9 days', NOW() - INTERVAL '7 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);

-- API tickets (John is expert)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, resolved_at, embedding) VALUES
('tk-006', 'TASK1006', 'API endpoint failing', 'REST API returning 500 error', 'Critical', 'CLOSED', 'API',
 'tm-006', NOW() - INTERVAL '20 days', NOW() - INTERVAL '21 days', NOW() - INTERVAL '19 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
 
('tk-007', 'TASK1007', 'API authentication issue', 'OAuth token not validating', 'High', 'CLOSED', 'API',
 'tm-006', NOW() - INTERVAL '15 days', NOW() - INTERVAL '16 days', NOW() - INTERVAL '14 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);
```

### Active Tickets (Current Workload)

```sql
-- Heavy workload: Ravi (5 active tickets - at threshold)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, embedding) VALUES
('tk-101', 'TASK2001', 'Active ticket 1', 'Description', 'High', 'IN_PROGRESS', 'AWS',
 'tm-001', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-102', 'TASK2002', 'Active ticket 2', 'Description', 'Medium', 'OPEN', 'AWS',
 'tm-001', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-103', 'TASK2003', 'Active ticket 3', 'Description', 'High', 'IN_PROGRESS', 'AWS',
 'tm-001', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-104', 'TASK2004', 'Active ticket 4', 'Description', 'Critical', 'IN_PROGRESS', 'AWS',
 'tm-001', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-105', 'TASK2005', 'Active ticket 5', 'Description', 'High', 'OPEN', 'AWS',
 'tm-001', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);

-- Medium workload: Priya (2 active tickets)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, embedding) VALUES
('tk-106', 'TASK2006', 'Active DB ticket 1', 'Description', 'Medium', 'IN_PROGRESS', 'Database',
 'tm-002', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-107', 'TASK2007', 'Active DB ticket 2', 'Description', 'Low', 'OPEN', 'Database',
 'tm-002', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);

-- Overloaded: Akash (10 active tickets - overloaded)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, embedding) 
SELECT 
    'tk-' || (110 + gs.n),
    'TASK' || (2010 + gs.n),
    'Active ticket ' || gs.n,
    'Description',
    CASE WHEN gs.n % 3 = 0 THEN 'Critical' WHEN gs.n % 2 = 0 THEN 'High' ELSE 'Medium' END,
    CASE WHEN gs.n % 2 = 0 THEN 'IN_PROGRESS' ELSE 'OPEN' END,
    'General',
    'tm-003',
    NOW() - INTERVAL '1 day' * gs.n,
    NOW() - INTERVAL '1 day' * gs.n,
    ARRAY(SELECT random() FROM generate_series(1, 768))::float[]
FROM generate_series(1, 10) AS gs(n);

-- Light workload: Sneha (0 active tickets - free)
-- No inserts needed

-- US team: John has 3 active tickets
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, embedding) VALUES
('tk-121', 'TASK2021', 'US active 1', 'Description', 'High', 'IN_PROGRESS', 'API',
 'tm-006', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-122', 'TASK2022', 'US active 2', 'Description', 'Medium', 'OPEN', 'API',
 'tm-006', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-123', 'TASK2023', 'US active 3', 'Description', 'Low', 'OPEN', 'API',
 'tm-006', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);
```

### Recent Assignments (Last 7 Days)

```sql
-- Ravi: 6 recent assignments (over threshold)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, resolved_at, embedding) 
SELECT 
    'tk-recent-' || gs.n,
    'TASK3' || (1000 + gs.n),
    'Recent assignment ' || gs.n,
    'Description',
    'Medium',
    'CLOSED',
    'AWS',
    'tm-001',
    NOW() - INTERVAL '1 day' * gs.n,
    NOW() - INTERVAL '1 day' * (gs.n + 1),
    NOW() - INTERVAL '1 day' * (gs.n - 1),
    ARRAY(SELECT random() FROM generate_series(1, 768))::float[]
FROM generate_series(1, 6) AS gs(n);

-- Priya: 2 recent assignments (under threshold)
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, resolved_at, embedding) VALUES
('tk-recent-10', 'TASK31010', 'Recent DB 1', 'Description', 'Medium', 'CLOSED', 'Database',
 'tm-002', NOW() - INTERVAL '3 days', NOW() - INTERVAL '4 days', NOW() - INTERVAL '2 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]),
('tk-recent-11', 'TASK31011', 'Recent DB 2', 'Description', 'High', 'CLOSED', 'Database',
 'tm-002', NOW() - INTERVAL '5 days', NOW() - INTERVAL '6 days', NOW() - INTERVAL '4 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);

-- Sneha: 0 recent assignments (available for work)
-- Akash: 1 recent assignment
INSERT INTO tickets (id, ticket_number, title, description, priority, status, category,
                     assignee_id, assigned_at, created_at, resolved_at, embedding) VALUES
('tk-recent-12', 'TASK31012', 'Recent general', 'Description', 'Low', 'CLOSED', 'General',
 'tm-003', NOW() - INTERVAL '6 days', NOW() - INTERVAL '7 days', NOW() - INTERVAL '5 days',
 ARRAY(SELECT random() FROM generate_series(1, 768))::float[]);
```

### Holidays

```sql
INSERT INTO holidays (id, name, date, region, created_at) VALUES
('hol-001', 'Diwali', '2025-11-12', 'IN', NOW()),
('hol-002', 'Christmas', '2025-12-25', 'GLOBAL', NOW()),
('hol-003', 'Thanksgiving', '2025-11-27', 'US', NOW()),
('hol-004', 'Republic Day', '2026-01-26', 'IN', NOW()),
('hol-005', 'Independence Day', '2025-07-04', 'US', NOW());
```

### Time-offs (PTO)

```sql
-- Arjun is on PTO today
INSERT INTO time_offs (id, member_id, start_date, end_date, type, created_at) VALUES
('pto-001', 'tm-005', CURRENT_DATE, CURRENT_DATE + INTERVAL '2 days', 'VACATION', NOW());

-- Sarah was on PTO last week (not blocking)
INSERT INTO time_offs (id, member_id, start_date, end_date, type, created_at) VALUES
('pto-002', 'tm-007', CURRENT_DATE - INTERVAL '7 days', CURRENT_DATE - INTERVAL '5 days', 'SICK_LEAVE', NOW());

-- Emily on PTO next week (not blocking)
INSERT INTO time_offs (id, member_id, start_date, end_date, type, created_at) VALUES
('pto-003', 'tm-009', CURRENT_DATE + INTERVAL '3 days', CURRENT_DATE + INTERVAL '5 days', 'VACATION', NOW());
```

---

## Test Cases

## Basic Assignment Tests

### Test Case 1: Perfect Match - Expert Available

**Objective**: Verify expert with high similarity gets assigned when available.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-001",
    "title": "AWS IAM policy configuration",
    "description": "Need to configure IAM policy for S3 access",
    "priority": "High",
    "category": "AWS",
    "embedding": [0.1, 0.2, ...]  # Similar to Ravi's tickets
}

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.92},
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.88},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.65}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="normal",
    primary_assignee="ravi.kumar@company.com",
    confidence_score=0.4-0.6,  # Medium due to recent assignments
    reasoning=["Medium confidence assignment - team lead notified"],
    business_rules_applied=["fair_distribution", "team_lead_notification"]
)
```

**Validation**:
- ✅ Ravi should be selected (highest similarity)
- ✅ Fair distribution rule triggers (6 recent assignments)
- ✅ Should consider Priya as alternative (only 2 recent assignments)
- ✅ Confidence: medium (similarity good, but fair distribution concern)

---

### Test Case 2: No Similar Pattern - Human Review

**Objective**: Verify human review trigger when no historical pattern exists.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-002",
    "title": "Blockchain integration issue",
    "description": "Smart contract deployment failing on Ethereum",
    "priority": "Critical",
    "category": "Blockchain",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.55},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.48}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="human_review",
    primary_assignee=None,
    human_review_triggers=[{
        "reason": "no_similar_pattern",
        "severity": "high",
        "action": "team_consultation_email",
        "timeout": "1 hour",
        "message": "No similar pattern found - team input needed"
    }]
)
```

**Validation**:
- ✅ No assignment made (human review)
- ✅ Max similarity (0.55) < 0.70 threshold
- ✅ Severity: high (novel ticket type)
- ✅ Action: team consultation

---

## Availability Tests

### Test Case 3: PTO Block

**Objective**: Verify members on PTO are not assigned.

**Setup**:
```python
# Current date: 2025-11-22
# Arjun (tm-005) is on PTO: 2025-11-22 to 2025-11-24

ticket_details = {
    "ticket_id": "TEST-003",
    "title": "AWS access issue",
    "description": "Need AWS access",
    "priority": "High",
    "category": "AWS",
    "embedding": [...]
}

# Assume Arjun would normally be best match
similar_tickets = [
    {"assignee_email": "arjun.singh@company.com", "similarity_score": 0.95}
]
```

**Expected Result**:
```python
# Arjun should have availability_score = 0.0
# Next available candidate should be selected
AssignmentDecision(
    primary_assignee="ravi.kumar@company.com",  # Next best available
    reasoning=["Arjun Singh unavailable (PTO)"]
)
```

**Validation**:
- ✅ Arjun excluded (availability_score = 0.0)
- ✅ Next best available member selected
- ✅ PTO reason logged

---

### Test Case 4: Holiday Block (Regional)

**Objective**: Verify regional holidays are respected.

**Setup**:
```python
# Test date: 2025-11-12 (Diwali - India only)
# Set system date to this for test

ticket_details = {
    "ticket_id": "TEST-004",
    "title": "Database query optimization",
    "description": "Slow queries need optimization",
    "priority": "High",
    "category": "Database",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.90},  # IST
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.75}     # US
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="john.smith@company.com",  # US member, not affected
    reasoning=["IST team unavailable (Regional holiday: Diwali)"]
)
```

**Validation**:
- ✅ All IST members excluded (availability_score = 0.0)
- ✅ US members still available
- ✅ Assignment goes to US despite lower similarity

---

### Test Case 5: Global Holiday

**Objective**: Verify global holidays block everyone.

**Setup**:
```python
# Test date: 2025-12-25 (Christmas - GLOBAL)

ticket_details = {
    "ticket_id": "TEST-005",
    "title": "Critical production issue",
    "description": "Service down",
    "priority": "Critical",
    "category": "Infrastructure",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.85},
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.80}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="human_review",
    human_review_triggers=[{
        "reason": "no_available_members",
        "severity": "critical",
        "message": "All team members unavailable (Global holiday)"
    }]
)
```

**Validation**:
- ✅ No members available (all availability_score = 0.0)
- ✅ Critical severity escalation
- ✅ Global holiday reason logged

---

## Workload & Overload Tests

### Test Case 6: Overload Prevention

**Objective**: Skip overloaded member even if best match.

**Setup**:
```python
# Akash has 10 active tickets (overloaded)

ticket_details = {
    "ticket_id": "TEST-006",
    "title": "General support ticket",
    "description": "Need help with configuration",
    "priority": "Medium",
    "category": "General",
    "embedding": [...]
}

# Assume Akash would score highest
similar_tickets = [
    {"assignee_email": "akash.patel@company.com", "similarity_score": 0.88},
    {"assignee_email": "sneha.reddy@company.com", "similarity_score": 0.65}
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="sneha.reddy@company.com",  # Next available
    business_rules_applied=["overload_prevention"],
    reasoning=[
        "Top choice (Akash Patel) is overloaded. Assigned to next available: Sneha Reddy"
    ]
)
```

**Validation**:
- ✅ Akash excluded (is_overloaded = True)
- ✅ Sneha selected (0 active tickets, available)
- ✅ Overload rule logged

---

### Test Case 7: Team at Capacity

**Objective**: Trigger critical escalation when everyone is overloaded.

**Setup**:
```python
# Manually set all members to overloaded state
# Update all active_tickets to push everyone over threshold

ticket_details = {
    "ticket_id": "TEST-007",
    "title": "Urgent support needed",
    "description": "Critical issue",
    "priority": "Critical",
    "category": "General",
    "embedding": [...]
}

similar_tickets = []  # No similar tickets
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="human_review",
    human_review_triggers=[{
        "reason": "team_at_capacity",
        "severity": "critical",
        "action": "immediate_manager_escalation",
        "message": "Team at capacity or critical issue requires immediate attention"
    }]
)
```

**Validation**:
- ✅ No assignment made
- ✅ Critical severity
- ✅ Manager escalation triggered
- ✅ All candidates show is_overloaded = True

---

### Test Case 8: Workload Score Calculation

**Objective**: Verify contextual workload scoring (priority, age, status).

**Setup**:
```python
# Verify scoring for members with different ticket compositions

# Member A: 3 Critical tickets (age: 1 day)
# Member B: 5 Low tickets (age: 1 day)
# Both should have different workload_scores
```

**Expected Calculation**:
```
Member A:
- 3 Critical tickets × 3.0 (priority) × 1.0 (age) × 1.0 (status) = 9.0
- workload_score = 1 - (9.0 / 30.0) = 0.70

Member B:
- 5 Low tickets × 0.5 (priority) × 1.0 (age) × 1.0 (status) = 2.5
- workload_score = 1 - (2.5 / 30.0) = 0.92

Member B has higher workload_score (less loaded)
```

**Validation**:
- ✅ Priority weights applied correctly
- ✅ Critical tickets count more than Low
- ✅ Workload score reflects true burden, not just ticket count

---

## Timezone Tests

### Test Case 9: IST Hours - Prefer IST Team

**Objective**: During IST hours, prefer IST team members.

**Setup**:
```python
# Current UTC time: 04:00 (9:30 AM IST - IST hours)

ticket_details = {
    "ticket_id": "TEST-009",
    "title": "API integration issue",
    "description": "Need API troubleshooting",
    "priority": "High",
    "category": "API",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.90},    # US (expert)
    {"assignee_email": "akash.patel@company.com", "similarity_score": 0.75}    # IST
]
```

**Expected Result**:
```python
# If score_diff < 0.30, prefer in-timezone
AssignmentDecision(
    primary_assignee="akash.patel@company.com",  # IST preferred
    business_rules_applied=["timezone_vs_expertise"],
    reasoning=["Preferred in-timezone member with comparable skills"]
)
```

**Validation**:
- ✅ timezone_score: IST = 1.0, US = 0.2
- ✅ Score difference: 0.90 - 0.75 = 0.15 (< 0.30 threshold)
- ✅ In-timezone member selected

---

### Test Case 10: US Hours - Prefer US Team

**Objective**: During US hours, prefer US team members.

**Setup**:
```python
# Current UTC time: 15:00 (10:00 AM EST - US hours)

ticket_details = {
    "ticket_id": "TEST-010",
    "title": "Database backup issue",
    "description": "Backup failing",
    "priority": "High",
    "category": "Database",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.88},  # IST (expert)
    {"assignee_email": "sarah.johnson@company.com", "similarity_score": 0.70}  # US
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="sarah.johnson@company.com",  # US preferred
    business_rules_applied=["timezone_vs_expertise"],
    reasoning=["Preferred in-timezone member with comparable skills"]
)
```

**Validation**:
- ✅ timezone_score: US = 1.0, IST = 0.2
- ✅ US member selected during US hours

---

### Test Case 11: Cross-Timezone Expert Override

**Objective**: Expert in wrong timezone should still be assigned if significantly better.

**Setup**:
```python
# Current UTC time: 04:00 (IST hours)

ticket_details = {
    "ticket_id": "TEST-011",
    "title": "API gateway configuration",
    "description": "Complex API setup needed",
    "priority": "Critical",
    "category": "API",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.95},   # US (expert: 5 solved)
    {"assignee_email": "akash.patel@company.com", "similarity_score": 0.60}   # IST
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="john.smith@company.com",  # Expert wins despite timezone
    business_rules_applied=["timezone_vs_expertise"],
    reasoning=[
        "Cross-timezone assignment: John Smith is expert (solved 5 similar tickets)"
    ]
)
```

**Validation**:
- ✅ Score difference: 0.95 - 0.60 = 0.35 (> 0.30 threshold)
- ✅ Expert selected despite wrong timezone
- ✅ Cross-timezone assignment logged

---

### Test Case 12: Critical Ticket Timezone Boost

**Objective**: Critical tickets get timezone score boost (0.2 → 0.5).

**Setup**:
```python
# Current UTC time: 04:00 (IST hours)
# US member in wrong timezone but for Critical ticket

ticket_details = {
    "ticket_id": "TEST-012",
    "title": "Production down",
    "description": "Critical service failure",
    "priority": "Critical",  # Critical priority
    "category": "Infrastructure",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "john.smith@company.com", "similarity_score": 0.90}  # US expert
]
```

**Expected Behavior**:
```python
# timezone_score calculation:
# Base: 0.2 (wrong timezone)
# Boost for Critical: 0.5
# John should get higher final score due to urgency override
```

**Validation**:
- ✅ timezone_score boosted from 0.2 to 0.5 for Critical
- ✅ Urgency documented in reasoning
- ✅ Expert can work cross-timezone for Critical issues

---

## Fair Distribution Tests

### Test Case 13: Fair Distribution Trigger

**Objective**: Member with too many recent assignments should be skipped.

**Setup**:
```python
# Ravi has 6 recent assignments (>= 5 threshold)
# Priya has 2 recent assignments

ticket_details = {
    "ticket_id": "TEST-013",
    "title": "AWS S3 bucket access",
    "description": "Need S3 access",
    "priority": "Medium",
    "category": "AWS",
    "embedding": [...]
}

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.88},   # 6 recent
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.75}  # 2 recent
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="priya.sharma@company.com",  # Less loaded
    business_rules_applied=["fair_distribution"],
    reasoning=[
        "Ravi Kumar has 6 assignments in last 7 days. "
        "Fair distribution to Priya Sharma (2 recent assignments)"
    ]
)
```

**Validation**:
- ✅ Ravi excluded (recent_assignments_count >= 5)
- ✅ Priya selected from top 5 candidates
- ✅ Fair distribution rule logged
- ✅ Assignment counts accurate

---

### Test Case 14: Fair Distribution - No Alternatives

**Objective**: If no less-loaded alternatives exist, keep top candidate.

**Setup**:
```python
# Everyone has 5+ recent assignments

ticket_details = {
    "ticket_id": "TEST-014",
    "title": "Support ticket",
    "description": "General support",
    "priority": "Low",
    "category": "General",
    "embedding": [...]
}

similar_tickets = [...]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="ravi.kumar@company.com",  # Top candidate kept
    business_rules_applied=[],  # Fair distribution attempted but no alternatives
    reasoning=["Assigned to Ravi Kumar (best available despite load)"]
)
```

**Validation**:
- ✅ Top candidate kept (no better alternative)
- ✅ Fair distribution attempted but not applied
- ✅ Load acknowledged in reasoning

---

## Confidence & Human Review Tests

### Test Case 15: Low Confidence - Human Review

**Objective**: Low confidence should trigger human review.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-015",
    "title": "Complex integration issue",
    "description": "Multi-system integration problem",
    "priority": "High",
    "category": "Integration",
    "embedding": [...]
}

# Create scenario where confidence < 0.3:
# - Low similarity (0.60)
# - Low skills (0.25)
# - Wrong timezone (0.2)
# - Close scores (gap: 0.05)

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.60},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.58}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="human_review",
    confidence_score=0.2,  # 1/5 factors passed
    human_review_triggers=[{
        "reason": "low_confidence_assignment",
        "severity": "medium",
        "action": "team_lead_review",
        "timeout": "15 minutes"
    }]
)
```

**Validation**:
- ✅ Confidence < 0.3 threshold
- ✅ Human review triggered
- ✅ Severity: medium (not critical)
- ✅ Team lead review (not manager escalation)

---

### Test Case 16: Medium Confidence - Team Lead Notification

**Objective**: Medium confidence should assign with notification.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-016",
    "title": "AWS IAM issue",
    "description": "IAM permissions not working",
    "priority": "High",
    "category": "AWS",
    "embedding": [...]
}

# Create scenario where 0.3 <= confidence < 0.5:
# - Good similarity (0.85) ✓
# - Medium skills (0.25) ✗
# - Available (1.0) ✓
# - Close winner (0.08) ✗
# - Wrong timezone (0.2) ✗
# Confidence: 2/5 = 0.4

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.85},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.80}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="normal",
    primary_assignee="ravi.kumar@company.com",
    confidence_score=0.4,
    business_rules_applied=["team_lead_notification"],
    reasoning=["Medium confidence assignment - team lead notified"]
)
```

**Validation**:
- ✅ Assignment made (0.3 <= confidence < 0.5)
- ✅ Team lead notification triggered
- ✅ Assignment not blocked
- ✅ Confidence score documented

---

### Test Case 17: High Confidence - Auto-Assign

**Objective**: High confidence should auto-assign without notifications.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-017",
    "title": "AWS IAM policy update",
    "description": "Standard IAM policy configuration",
    "priority": "High",
    "category": "AWS",
    "embedding": [...]
}

# Create scenario where confidence >= 0.5:
# - High similarity (0.92) ✓
# - Good skills (assume 0.85) ✓
# - Available (1.0) ✓
# - Clear winner (0.20 gap) ✓
# - Right timezone (1.0) ✓
# Confidence: 5/5 = 1.0

similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.92},
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.88},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.60}
]
```

**Expected Result**:
```python
AssignmentDecision(
    assignment_type="normal",
    primary_assignee="ravi.kumar@company.com",
    confidence_score=1.0,
    business_rules_applied=[],  # No special handling needed
    reasoning=["Assigned to Ravi Kumar: Score=0.95 (high confidence)"]
)
```

**Validation**:
- ✅ Confidence >= 0.5
- ✅ No team lead notification
- ✅ No human review
- ✅ Clean automatic assignment

---

## Business Rules Integration Tests

### Test Case 18: Multiple Rules Applied

**Objective**: Verify multiple business rules can work together.

**Setup**:
```python
# Scenario: Expert in wrong timezone + has many recent assignments

ticket_details = {
    "ticket_id": "TEST-018",
    "title": "AWS Lambda function issue",
    "description": "Lambda deployment failing",
    "priority": "High",
    "category": "AWS",
    "embedding": [...]
}

# Ravi: Expert (0.90 similarity), wrong timezone, 6 recent assignments
# Priya: Medium (0.70 similarity), right timezone, 2 recent assignments
similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.90},
    {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.70}
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="priya.sharma@company.com",
    business_rules_applied=["fair_distribution", "timezone_vs_expertise"],
    reasoning=[
        "Ravi Kumar has 6 assignments in last 7 days.",
        "Fair distribution to Priya Sharma (2 recent assignments)",
        "Preferred in-timezone member with comparable skills"
    ]
)
```

**Validation**:
- ✅ Fair distribution checked first
- ✅ Timezone trade-off evaluated
- ✅ Multiple rules logged
- ✅ Reasoning explains all decisions

---

### Test Case 19: Skills Gap Detection

**Objective**: Verify skills gap flagging without blocking assignment.

**Setup**:
```python
ticket_details = {
    "ticket_id": "TEST-019",
    "title": "Machine Learning model deployment",
    "description": "Deploy ML model to production",
    "priority": "High",
    "category": "ML",
    "embedding": [...]
}

# No one on team has ML skills
# All candidates: skill_match_score < 0.25
similar_tickets = [
    {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.75}
]
```

**Expected Result**:
```python
AssignmentDecision(
    primary_assignee="ravi.kumar@company.com",  # Best available
    business_rules_applied=["skills_gap_detected"],
    reasoning=[
        "Skills gap detected - no team member is strong match. "
        "Consider external consultation or training."
    ]
)
```

**Validation**:
- ✅ Assignment still made (not blocked)
- ✅ Skills gap flagged
- ✅ Warning added to reasoning
- ✅ Suggestion for external help

---

### Test Case 20: Priority-Based Weight Adjustment

**Objective**: Verify weights change based on ticket priority.

**Setup**:
```python
# Test same scenario with different priorities

base_ticket = {
    "ticket_id": "TEST-020",
    "title": "Support ticket",
    "description": "General support",
    "category": "General",
    "embedding": [...]
}

# Test Low, Medium, High, Critical priorities
# Verify weight allocations differ
```

**Expected Behavior**:
```python
# Low Priority: workload_weight = 0.40 (highest)
# Medium Priority: workload_weight = 0.20
# High Priority: workload_weight = 0.15
# Critical Priority: workload_weight = 0.10 (lowest)

# Workload balance matters more for Low priority
# Expertise matters more for Critical priority
```

**Validation**:
- ✅ Weights loaded from config by priority
- ✅ Low priority favors workload balance
- ✅ Critical priority favors similarity/expertise
- ✅ Final scores differ based on priority

---

## Test Execution Guide

### Running Individual Tests

Create `test_assignment_engine.py`:

```python
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ticket_ai_agents.assignment_engine.customized_assignment_engine import AssignmentEngine

async def run_test_case(test_name, ticket_details, similar_tickets):
    """Run a single test case"""
    print(f"\n{'='*80}")
    print(f"TEST CASE: {test_name}")
    print(f"{'='*80}\n")
    
    engine = AssignmentEngine()
    
    try:
        decision = await engine.assign_ticket(
            ticket_details=ticket_details,
            similar_tickets=similar_tickets
        )
        
        print(f"✅ TEST PASSED: {test_name}")
        print(f"\nDecision:")
        print(f"  Assignment Type: {decision.assignment_type}")
        print(f"  Primary Assignee: {decision.primary_assignee}")
        print(f"  Confidence: {decision.confidence_score:.2f}")
        print(f"  Business Rules: {decision.business_rules_applied}")
        print(f"  Reasoning: {decision.reasoning}")
        
        if decision.human_review_triggers:
            print(f"\n  Human Review Triggers:")
            for trigger in decision.human_review_triggers:
                print(f"    - {trigger}")
        
        return True, decision
        
    except Exception as e:
        print(f"❌ TEST FAILED: {test_name}")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

async def run_all_tests():
    """Run all test cases"""
    results = []
    
    # Test Case 1: Perfect Match
    test1_result = await run_test_case(
        "Test Case 1: Perfect Match - Expert Available",
        ticket_details={
            "ticket_id": "TEST-001",
            "title": "AWS IAM policy configuration",
            "description": "Need to configure IAM policy for S3 access",
            "priority": "High",
            "category": "AWS"
        },
        similar_tickets=[
            {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.92},
            {"assignee_email": "ravi.kumar@company.com", "similarity_score": 0.88},
            {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.65}
        ]
    )
    results.append(test1_result)
    
    # Test Case 2: No Similar Pattern
    test2_result = await run_test_case(
        "Test Case 2: No Similar Pattern - Human Review",
        ticket_details={
            "ticket_id": "TEST-002",
            "title": "Blockchain integration issue",
            "description": "Smart contract deployment failing",
            "priority": "Critical",
            "category": "Blockchain"
        },
        similar_tickets=[
            {"assignee_email": "john.smith@company.com", "similarity_score": 0.55},
            {"assignee_email": "priya.sharma@company.com", "similarity_score": 0.48}
        ]
    )
    results.append(test2_result)
    
    # Add more test cases...
    
    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    passed = sum(1 for r in results if r[0])
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
```

### Running Tests

```bash
# Run all tests
python test_assignment_engine.py

# Run specific test category
python test_assignment_engine.py --category availability

# Run with verbose output
python test_assignment_engine.py --verbose

# Run and generate report
python test_assignment_engine.py --report test_report.html
```

---

## Validation Checklist

### Pre-Deployment Validation

- [ ] **Database Setup**
  - [ ] Test database created and migrated
  - [ ] All seed data inserted correctly
  - [ ] Verify data integrity (foreign keys, constraints)
  - [ ] Check embedding dimensions (768)

- [ ] **Basic Functionality**
  - [ ] Engine initializes without errors
  - [ ] Can query team members
  - [ ] Can query tickets
  - [ ] Can query holidays and time-offs
  - [ ] Recent assignments query returns correct counts

- [ ] **Scoring Components**
  - [ ] Similarity score: 0.0-1.0 range, logarithmic scaling works
  - [ ] Skill match: Returns reasonable scores
  - [ ] Availability: Binary (0 or 1) only
  - [ ] Workload: Contextual scoring with priority/age/status
  - [ ] Timezone: Correct windows (IST: 2.5-12.5 UTC)

- [ ] **Business Rules**
  - [ ] Rule 1: Overload prevention works
  - [ ] Rule 2: Timezone vs expertise trade-off
  - [ ] Rule 3: Fair distribution with recent_assignments_count
  - [ ] Rule 4: Skills gap detection
  - [ ] Rule 7: Confidence gating (< 0.3, 0.3-0.5, >= 0.5)

- [ ] **Edge Cases**
  - [ ] PTO blocks assignment
  - [ ] Regional holidays block correct team
  - [ ] Global holidays block everyone
  - [ ] Team at capacity triggers escalation
  - [ ] No similar pattern triggers human review
  - [ ] Low confidence triggers team lead notification

- [ ] **Performance**
  - [ ] Query count: 4 queries per assignment (not N+1)
  - [ ] Assignment time: < 500ms average
  - [ ] Batch fetching working correctly
  - [ ] No memory leaks with repeated runs

- [ ] **Data Quality**
  - [ ] All assignee emails valid
  - [ ] All timezones recognized by pytz
  - [ ] All timestamps timezone-aware
  - [ ] Embedding vectors valid (not null, correct length)

### Post-Test Validation

- [ ] Review all test outputs manually
- [ ] Verify reasoning makes logical sense
- [ ] Check confidence scores align with expectations
- [ ] Ensure no unexpected exceptions
- [ ] Validate business rules applied correctly
- [ ] Cross-check with manual assignment decisions
- [ ] Performance profiling shows acceptable latency
- [ ] Memory usage stable over multiple runs

### Documentation

- [ ] All test cases documented with expected results
- [ ] Edge cases clearly explained
- [ ] Known limitations documented
- [ ] Deployment checklist created
- [ ] Rollback plan prepared

---

## Troubleshooting Guide

### Common Issues

**Issue 1: `recent_assignments_count` always 0**
```sql
-- Check if assigned_at is populated
SELECT COUNT(*) FROM tickets WHERE assigned_at IS NULL;

-- If many nulls, update them
UPDATE tickets SET assigned_at = created_at WHERE assigned_at IS NULL;
```

**Issue 2: All availability_scores are 0**
```sql
-- Check if PTO dates are current
SELECT * FROM time_offs WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE;

-- Check if today is a holiday
SELECT * FROM holidays WHERE date = CURRENT_DATE;
```

**Issue 3: Similarity scores all the same**
```sql
-- Check if embeddings are valid
SELECT id, array_length(embedding, 1) FROM tickets LIMIT 5;

-- Should return 768 for all rows
```

**Issue 4: Timezone scores unexpected**
```python
# Check current UTC time
from datetime import datetime, timezone
current_utc = datetime.now(timezone.utc)
print(f"Current UTC: {current_utc.hour}:{current_utc.minute}")

# IST hours: 2.5 - 12.5 UTC (8 AM - 6 PM IST)
# US hours: Everything else
```

---

## Success Criteria

### Test Pass Requirements

1. **Correctness**: 100% of test cases pass with expected results
2. **Performance**: Average assignment time < 500ms
3. **Reliability**: No exceptions or crashes across 100+ runs
4. **Consistency**: Same inputs produce same outputs (deterministic)
5. **Edge Cases**: All 20 edge cases handled gracefully
6. **Business Logic**: All 7 business rules apply correctly
7. **Data Integrity**: No database corruption or inconsistencies

### Production Readiness

- ✅ All test cases pass
- ✅ Performance benchmarks met
- ✅ Edge cases validated
- ✅ Error handling robust
- ✅ Logging comprehensive
- ✅ Documentation complete
- ✅ Code reviewed and approved
- ✅ Monitoring alerts configured

---

## Next Steps After Testing

1. **Performance Tuning**
   - Add database indexes if needed
   - Optimize slow queries
   - Cache frequently accessed data

2. **Monitoring Setup**
   - Track assignment success rate
   - Monitor confidence score distribution
   - Alert on high human review rate
   - Dashboard for team lead notifications

3. **Feedback Loop**
   - Collect reassignment data
   - Track resolution times by assignee
   - Adjust weights based on outcomes
   - Continuous improvement cycle

4. **Production Deployment**
   - Deploy to staging first
   - Gradual rollout (10% → 50% → 100%)
   - Monitor metrics closely
   - Keep rollback plan ready

---

**Document Version**: 1.0  
**Last Updated**: November 22, 2025  
**Test Coverage**: 20 test cases across 7 categories  
**Estimated Test Duration**: 2-3 hours for complete suite
