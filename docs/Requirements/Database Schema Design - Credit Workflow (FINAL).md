---
tags:
---
# Credit Risk Workflow Database Schema Design (Updated)

This document outlines the updated comprehensive database schema for the Credit Risk Workflow Tool. The schema has been revised to incorporate draft management requirements for parallel processing components and the updated workflow state model.

## Table of Contents

- Entity Relationship Overview
- Core Models
- User and Role Management
- Workflow Management
- Credit Request Components
- Document Management
- Tracking and Notifications
- Key Relationships Explained
- Draft Management Implementation

## Entity Relationship Overview

The database schema is built around several key entities:

- Users and their roles
- Credit requests and their components
- Workflow states and transitions
- Documents and their management with draft capabilities
- Tracking and notification systems

## Core Models

### User Model

```
User:
  - id: UUID (PK)
  - username: VARCHAR(50)
  - email: VARCHAR(100)
  - password: VARCHAR(100) (hashed)
  - first_name: VARCHAR(50)
  - last_name: VARCHAR(50)
  - department_id: UUID (FK to Department)
  - role_id: UUID (FK to Role)
  - is_active: BOOLEAN
  - last_login: DATETIME
  - created_at: DATETIME
  - updated_at: DATETIME
```

### CounterParty Model

```
CounterParty:
  - id: UUID (PK)
  - name: VARCHAR(200)
  - cif_number: VARCHAR(50)
  - country_of_risk: VARCHAR(100)
  - has_guarantor: BOOLEAN
  - guarantor_details: TEXT (NULL if no guarantor)
  - rating_current: VARCHAR(10)
  - rating_previous: VARCHAR(10)
  - sp_rating: VARCHAR(10)
  - moodys_rating: VARCHAR(10)
  - fitch_rating: VARCHAR(10)
  - created_at: DATETIME
  - updated_at: DATETIME
```

### CreditRequest Model

```
CreditRequest:
  - id: UUID (PK)
  - request_number: VARCHAR(20) (auto-generated)
  - counterparty_id: UUID (FK to CounterParty)
  - workflow_state_id: UUID (FK to WorkflowState)
  - submitter_id: UUID (FK to User - Relationship Manager)
  - assigned_analyst_id: UUID (FK to User - Credit Analyst, nullable)
  - business_sponsor_id: UUID (FK to User - Business Sponsor)
  - second_sponsor_id: UUID (FK to User - optional)
  - da_level: INTEGER (1-8, determined during Credit Review)
  - priority: ENUM('Low', 'Medium', 'High')
  - required_by_date: DATE
  - priority_justification: TEXT (required if priority is High)
  - revenue_last_12m: DECIMAL(15,2)
  - projected_revenue: DECIMAL(15,2)
  - projected_rorwa_percentage: DECIMAL(5,2)
  - country_risk_limit_confirmed: BOOLEAN
  - client_introduction_details: TEXT
  - kyc_approval_status: VARCHAR(50)
  - senior_client_contact: VARCHAR(100)
  - last_client_visit_date: DATE
  - has_legal_opinion: BOOLEAN
  - financial_statements_received: BOOLEAN
  - interim_financials_info: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
  - submitted_at: DATETIME
  - completed_at: DATETIME (nullable)
```

## User and Role Management

### Department Model

```
Department:
  - id: UUID (PK)
  - name: VARCHAR(100) (e.g., "Credit Risk", "Front Office", "Legal")
  - description: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
```

### Role Model

```
Role:
  - id: UUID (PK)
  - name: VARCHAR(50) (e.g., "Credit Analyst", "Relationship Manager")
  - description: TEXT
  - da_level: INTEGER (NULL for roles without DA level)
  - can_approve: BOOLEAN
  - can_submit: BOOLEAN
  - can_review: BOOLEAN
  - created_at: DATETIME
  - updated_at: DATETIME
```

### Permission Model

```
Permission:
  - id: UUID (PK)
  - name: VARCHAR(50)
  - code: VARCHAR(50)
  - description: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
```

### RolePermission Model (Join table)

```
RolePermission:
  - id: UUID (PK)
  - role_id: UUID (FK to Role)
  - permission_id: UUID (FK to Permission)
  - created_at: DATETIME
  - updated_at: DATETIME
```

## Workflow Management

### WorkflowState Model (Updated)

```
WorkflowState:
  - id: UUID (PK)
  - name: VARCHAR(50) (e.g., "Draft", "Submitted", "Business Sponsor Approved")
  - description: TEXT
  - is_initial_state: BOOLEAN
  - is_final_state: BOOLEAN
  - is_draft_state: BOOLEAN (NEW - indicates if this is a draft state)
  - parent_state_id: UUID (FK to WorkflowState, NULL for non-draft states) (NEW)
  - created_at: DATETIME
  - updated_at: DATETIME
```

### WorkflowStateTransition Model

```
WorkflowStateTransition:
  - id: UUID (PK)
  - from_state_id: UUID (FK to WorkflowState)
  - to_state_id: UUID (FK to WorkflowState)
  - required_role_id: UUID (FK to Role)
  - name: VARCHAR(100) (e.g., "Approve", "Reject", "Save as Draft", "Publish")
  - is_rejection: BOOLEAN
  - is_draft_save: BOOLEAN (NEW - indicates a save to draft action)
  - is_publication: BOOLEAN (NEW - indicates a publish action)
  - created_at: DATETIME
  - updated_at: DATETIME
```

## Credit Request Components

### LimitType Model

```
LimitType:
  - id: UUID (PK)
  - name: VARCHAR(100) (e.g., "Trading", "Nostro", "Loan", "Metal Lease")
  - code: VARCHAR(20)
  - description: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
```

### CreditLimit Model

```
CreditLimit:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - limit_type_id: UUID (FK to LimitType)
  - existing_limit_amount: DECIMAL(15,2)
  - existing_tenor_months: INTEGER
  - proposed_limit_amount: DECIMAL(15,2)
  - proposed_tenor_months: INTEGER
  - is_approved: BOOLEAN (nullable until decision made)
  - created_at: DATETIME
  - updated_at: DATETIME
```

### CreditQuestionnaire Model (Updated)

```
CreditQuestionnaire:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - preparer_id: UUID (FK to User - Relationship Manager)
  - is_required: BOOLEAN
  - is_completed: BOOLEAN
  - is_draft: BOOLEAN (NEW - indicates if current version is a draft)
  - published_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - latest_draft_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - business_model_details: TEXT
  - key_suppliers_customers: TEXT
  - trading_activity_rationale: TEXT
  - trading_flow_drivers: TEXT
  - position_size_determinants: TEXT
  - trading_policy_governance: TEXT
  - hedge_effectiveness: TEXT
  - hedge_accounting_approach: TEXT
  - stress_testing_methodology: TEXT
  - cash_management_approach: TEXT
  - notional_position_details: TEXT
  - liquidity_management: TEXT
  - banking_relationships: TEXT
  - physical_positions: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
  - last_draft_saved_at: DATETIME (NEW)
  - last_published_at: DATETIME (NEW)
  - completed_at: DATETIME (nullable)
```

### LegalReview Model (Updated)

```
LegalReview:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - reviewer_id: UUID (FK to User)
  - is_draft: BOOLEAN (NEW - indicates if current version is a draft)
  - published_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - latest_draft_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - agreement_type: VARCHAR(50) (e.g., "ISDA", "GMRA", "Bespoke")
  - termination_rights: TEXT
  - acceleration_clauses: TEXT
  - events_of_default: TEXT
  - settlement_provisions: TEXT
  - payment_flows: TEXT
  - setoff_rights: TEXT
  - limitations: TEXT
  - maturity_dates: TEXT
  - interest_payment_terms: TEXT
  - currency_pairs: TEXT
  - legal_commentary: TEXT
  - bankruptcy_limitations: TEXT
  - jurisdictional_issues: TEXT
  - other_legal_risks: TEXT
  - is_completed: BOOLEAN
  - created_at: DATETIME
  - updated_at: DATETIME
  - last_draft_saved_at: DATETIME (NEW)
  - last_published_at: DATETIME (NEW)
  - completed_at: DATETIME (nullable)
```

### CreditAnalysis Model (Updated)

```
CreditAnalysis:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - analyst_id: UUID (FK to User)
  - is_draft: BOOLEAN (NEW - indicates if current version is a draft)
  - published_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - latest_draft_version_id: UUID (FK to DocumentVersion, nullable) (NEW)
  - executive_summary: TEXT
  - counterparty_business: TEXT
  - ownership_details: TEXT
  - market_position: TEXT
  - financial_analysis: TEXT
  - rating_assessment: TEXT
  - climate_risk_assessment: TEXT
  - key_risk_analysis: TEXT
  - mitigating_factors: TEXT
  - macroeconomic_scenarios: TEXT
  - market_risk_sensitivities: TEXT
  - credit_recommendation: TEXT
  - recommendation_rationale: TEXT
  - is_completed: BOOLEAN
  - created_at: DATETIME
  - updated_at: DATETIME
  - last_draft_saved_at: DATETIME (NEW)
  - last_published_at: DATETIME (NEW)
  - completed_at: DATETIME (nullable)
```

### BusinessSponsorship Model

```
BusinessSponsorship:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - sponsor_id: UUID (FK to User)
  - second_sponsor_id: UUID (FK to User, nullable)
  - comments: TEXT
  - is_approved: BOOLEAN
  - created_at: DATETIME
  - updated_at: DATETIME
  - approved_at: DATETIME (nullable)
```

### ApprovalRecord Model

```
ApprovalRecord:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - approver_id: UUID (FK to User)
  - is_committee: BOOLEAN
  - committee_minutes: TEXT (nullable, only for committee approvals)
  - comments: TEXT
  - decision: ENUM('Approved', 'Rejected')
  - rejection_reason: TEXT (nullable, required if rejected)
  - created_at: DATETIME
  - updated_at: DATETIME
  - decided_at: DATETIME
```

## Document Management

### DocumentType Model

```
DocumentType:
  - id: UUID (PK)
  - name: VARCHAR(100) (e.g., "Credit Paper", "Financial Statement", "Committee Minutes")
  - description: TEXT
  - supports_drafts: BOOLEAN (NEW - indicates if this type supports draft functionality)
  - created_at: DATETIME
  - updated_at: DATETIME
```

### Document Model (Updated)

```
Document:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - document_type_id: UUID (FK to DocumentType)
  - name: VARCHAR(255)
  - current_version_id: UUID (FK to DocumentVersion) (NEW)
  - is_draft: BOOLEAN (NEW - indicates if current version is a draft)
  - uploader_id: UUID (FK to User)
  - created_at: DATETIME
  - updated_at: DATETIME
  - last_published_at: DATETIME (NEW)
```

### DocumentVersion Model (NEW)

```
DocumentVersion:
  - id: UUID (PK)
  - document_id: UUID (FK to Document)
  - file_path: VARCHAR(500)
  - file_size: INTEGER (in bytes)
  - mime_type: VARCHAR(100)
  - content: TEXT/BLOB (for inline content when applicable)
  - version_number: INTEGER
  - is_draft: BOOLEAN
  - creator_id: UUID (FK to User)
  - draft_name: VARCHAR(255) (NULL for published versions)
  - created_at: DATETIME
  - published_at: DATETIME (NULL for drafts)
```

### CreditPaper Model (NEW)

```
CreditPaper:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - credit_questionnaire_version_id: UUID (FK to DocumentVersion, nullable)
  - legal_review_version_id: UUID (FK to DocumentVersion, nullable)
  - credit_analysis_version_id: UUID (FK to DocumentVersion, nullable)
  - final_document_id: UUID (FK to Document, nullable)
  - is_complete: BOOLEAN
  - is_approved: BOOLEAN
  - created_at: DATETIME
  - updated_at: DATETIME
  - completed_at: DATETIME (nullable)
  - approved_at: DATETIME (nullable)
```

## Tracking and Notifications

### Comment Model

```
Comment:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - user_id: UUID (FK to User)
  - text: TEXT
  - created_at: DATETIME
  - updated_at: DATETIME
```

### History Model

```
History:
  - id: UUID (PK)
  - credit_request_id: UUID (FK to CreditRequest)
  - user_id: UUID (FK to User)
  - action: VARCHAR(255)
  - details: TEXT
  - previous_state_id: UUID (FK to WorkflowState, nullable)
  - new_state_id: UUID (FK to WorkflowState, nullable)
  - is_draft_action: BOOLEAN (NEW - indicates if this was a draft-related action)
  - created_at: DATETIME
```

### Notification Model

```
Notification:
  - id: UUID (PK)
  - user_id: UUID (FK to User)
  - credit_request_id: UUID (FK to CreditRequest, nullable)
  - title: VARCHAR(255)
  - message: TEXT
  - is_read: BOOLEAN
  - created_at: DATETIME
  - read_at: DATETIME (nullable)
```

### DocumentLock Model (NEW)

```
DocumentLock:
  - id: UUID (PK)
  - document_id: UUID (FK to Document)
  - user_id: UUID (FK to User)
  - lock_expiry: DATETIME
  - created_at: DATETIME
```

## Draft Management Implementation

### ComponentDraftState Model (NEW)

```
ComponentDraftState:
  - id: UUID (PK)
  - component_type: ENUM('CreditQuestionnaire', 'LegalReview', 'CreditAnalysis')
  - component_id: UUID (FK to respective component table)
  - user_id: UUID (FK to User)
  - is_currently_editing: BOOLEAN
  - last_activity: DATETIME
  - created_at: DATETIME
  - updated_at: DATETIME
```

### PublicationNote Model (NEW)

```
PublicationNote:
  - id: UUID (PK)
  - document_version_id: UUID (FK to DocumentVersion)
  - user_id: UUID (FK to User)
  - note: TEXT
  - created_at: DATETIME
```

## Key Relationships Explained

1. **User Relationships**:
    
    - Users belong to specific Departments (Credit Risk, Front Office, Legal, etc.)
    - Users have specific Roles (Credit Analyst, Relationship Manager, etc.)
    - Users can submit, review, and approve CreditRequests depending on their role
    - Users receive Notifications about relevant actions
2. **Role and Permission Relationships**:
    
    - Roles have specific Permissions defining what actions users can perform
    - Roles determine which WorkflowStateTransitions a user can execute
    - Some roles have specific DA (Delegated Authority) levels for approvals
3. **CreditRequest Workflow**:
    
    - CreditRequests progress through various WorkflowStates
    - WorkflowStateTransitions define valid movements between states
    - Each transition can be restricted to specific roles
    - History records all state changes and actions
4. **CreditRequest Components**:
    
    - CreditRequests contain multiple CreditLimits of different LimitTypes
    - CreditRequests are associated with a CounterParty
    - CreditRequests may require a CreditQuestionnaire (determined during Credit Review)
    - CreditRequests involve LegalReview and CreditAnalysis components
    - CreditRequests require BusinessSponsorship approval
    - ApprovalRecords track final decisions (individual or committee)
5. **Document Management**:
    
    - Documents are categorized by DocumentType
    - Documents are associated with specific CreditRequests
    - Documents have multiple DocumentVersions tracking revisions
    - DocumentVersions can be marked as drafts or published
    - ComponentDraftState tracks who is currently editing which component
    - DocumentLocks prevent conflicting edits
6. **Draft Management**:
    
    - Each component (CreditQuestionnaire, LegalReview, CreditAnalysis) can have:
        - A private draft version (only visible to creator)
        - A published version (visible to all authorized users)
    - Draft versions can be saved multiple times before publishing
    - Publication explicitly makes content visible to others
    - The CreditPaper dynamically assembles the latest published versions

## Key Database Design Considerations

1. **Workflow Flexibility**:
    - The WorkflowState and WorkflowStateTransition tables allow for configuration of the workflow without code changes
    - Future workflow modifications can be made by adding/modifying states and transitions
2. **Document Versioning and Draft Management**:
    - The DocumentVersion model supports both draft and published versions
    - Components can have private drafts while maintaining public published versions
    - Version history is maintained for audit and rollback purposes
3. **Parallel Process Support**:
    - The schema supports independent work on parallel components
    - Each component can track its own draft and publication state
    - CreditPaper dynamically assembles the latest published versions of all components
4. **Audit Trail**:
    - The History model tracks all significant actions across the system
    - Publication notes capture the context of why changes were published
    - This provides full visibility into the request lifecycle and user actions
5. **Role-Based Access Control**:
    - The Role and Permission models implement a flexible RBAC system
    - This allows for fine-grained control over who can perform specific actions
    - Different visibility rules apply to drafts vs. published content
6. **Concurrent Editing Protection**:
    - DocumentLock mechanism prevents multiple users from editing the same component simultaneously
    - Locks automatically expire after a configurable period
7. **Scalability**:
    - UUID primary keys allow for distributed systems in the future
    - Separate models for different components enable independent scaling
    - Draft management enables more efficient collaboration across teams
