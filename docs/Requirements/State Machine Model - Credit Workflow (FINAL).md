---
tags:
---
# Credit Risk Workflow State Machine Model

This document provides a comprehensive state machine model for the Credit Risk Workflow Tool, including all states, transitions, permissions, and actions required to facilitate the credit limit approval process with enhanced draft management capabilities.

## Table of Contents

1. Workflow States
2. Role Permissions
3. Workflow Transitions and Required Actions
4. Parallel Processing Model
5. Draft Management
6. State Transition Rules and Validations
7. Workflow Visualizations
8. Special Handling Notes

## 1. Workflow States

|State ID|State Name|Description|Is Initial|Is Final|Is Draft State|Parent State|
|---|---|---|---|---|---|---|
|S1|DRAFT|Initial state when a credit request is being created but not yet submitted|Yes|No|No|None|
|S2|SUBMITTED|Credit limit application has been submitted by Front Office|No|No|No|None|
|S3|CREDIT_REVIEW|Credit Risk is reviewing the application|No|No|No|None|


|S6|BUSINESS_SPONSORSHIP_PENDING|Awaiting approval from Business Sponsor|No|No|No|None|
|S7|BUSINESS_SPONSOR_APPROVED|Business Sponsor has approved, parallel processes can begin|No|No|No|None|
|S8|CREDIT_ANALYSIS_IN_PROGRESS|Credit Analysis being performed by Credit Analyst|No|No|No|None|
|S8D|CREDIT_ANALYSIS_DRAFT|Credit Analysis being drafted (private to Credit Analyst)|No|No|Yes|S8|
|S9|LEGAL_REVIEW_IN_PROGRESS|Legal Review being performed by Legal Reviewer|No|No|No|None|
|S9D|LEGAL_REVIEW_DRAFT|Legal Review being drafted (private to Legal Reviewer)|No|No|Yes|S9|
|S10|QUESTIONNAIRE_PENDING|Credit Questionnaire required and pending from Front Office|No|No|No|None|
|S10D|QUESTIONNAIRE_DRAFT|Credit Questionnaire being drafted (private to Front Office)|No|No|Yes|S10|
|S11|CREDIT_PAPER_COMPILATION|All components being compiled into final Credit Paper|No|No|No|None|
|S12|APPROVAL_PENDING_INDIVIDUAL|Awaiting individual approval (DA3-DA8)|No|No|No|None|
|S13|APPROVAL_PENDING_COMMITTEE|Awaiting committee approval (DA1-DA2)|No|No|No|None|
|S14|APPROVED|Credit request has been approved|No|Yes|No|None|
|S15|REJECTED|Credit request has been rejected|No|Yes|No|None|
|S16|CANCELLED|Credit request has been cancelled|No|Yes|No|None|

|S18|RETURNED_TO_CREDIT_ANALYSIS|Credit request returned to Credit Analysis for revision|No|No|No|None|

## 2. Role Permissions

|Role ID|Role Name|Description|Can Submit|Can Review|Can Approve|Can Draft|DA Level|
|---|---|---|---|---|---|---|---|
|R1|Relationship Manager|Front Office role that initiates credit requests|Yes|No|No|Yes|N/A|
|R2|Credit Analyst|Reviews and analyzes credit requests|No|Yes|No|Yes|N/A|
|R3|Credit Approver DA3|Credit Analyst with DA3 approval authority|No|Yes|Yes|Yes|3|
|R4|Credit Approver DA4|Credit Analyst with DA4 approval authority|No|Yes|Yes|Yes|4|
|R5|Credit Approver DA5|Credit Analyst with DA5 approval authority|No|Yes|Yes|Yes|5|
|R6|Credit Approver DA6|Credit Analyst with DA6 approval authority|No|Yes|Yes|Yes|6|
|R7|Credit Approver DA7|Credit Analyst with DA7 approval authority|No|Yes|Yes|Yes|7|
|R8|Credit Approver DA8|Credit Analyst with DA8 approval authority|No|Yes|Yes|Yes|8|
|R9|Committee Member|Participates in committee approvals|No|No|Yes|No|1-2|
|R10|Business Sponsor|Senior stakeholder who supports the request|No|No|Yes|No|N/A|
|R11|Legal Reviewer|Reviews legal documentation|No|Yes|No|Yes|N/A|
|R12|System Administrator|Manages system settings and user access|Yes|Yes|Yes|Yes|N/A|

## 3. Workflow Transitions and Required Actions

|Transition ID|From State|To State|Name|Required Role(s)|Actions Required|Is Draft Action|Notes|
|---|---|---|---|---|---|---|---|
|T1|DRAFT|SUBMITTED|Submit Application|R1|- Complete all required fields in Credit Limit Application<br>- Attach any initial supporting documents|No|Front Office submits the initial request, which must include counterparty details, proposed limits, and business rationale|
|T2|SUBMITTED|CREDIT_REVIEW|Begin Credit Review|R2, R3-R8|- Assign request to specific Credit Analyst<br>- Initial review of application completeness|No|Credit Risk department takes ownership of the request and begins initial assessment|

|T7|BUSINESS_SPONSORSHIP_PENDING|BUSINESS_SPONSOR_APPROVED|Approve as Business Sponsor|R10|- Provide approval with comments<br>- Record date of approval|No|Business Sponsor confirms support for the credit request|
|T8|BUSINESS_SPONSORSHIP_PENDING|REJECTED|Reject as Business Sponsor|R10|- Provide rejection reason<br>- Add comments explaining decision|No|Business Sponsor does not support the request|
|T9|BUSINESS_SPONSOR_APPROVED|CREDIT_ANALYSIS_IN_PROGRESS|Begin Credit Analysis|R2, R3-R8|- Start detailed credit analysis<br>- Gather financial data|No|Credit Analysis begins only after Business Sponsor approval|
|T10|BUSINESS_SPONSOR_APPROVED|LEGAL_REVIEW_IN_PROGRESS|Begin Legal Review|R11|- Start legal documentation analysis|No|Legal Review begins only after Business Sponsor approval|
|T11|BUSINESS_SPONSOR_APPROVED|QUESTIONNAIRE_PENDING|Request Credit Questionnaire|R2, R3-R8|- Mark Credit Questionnaire as required<br>- Notify Front Office|No|Only triggered if Credit Questionnaire was required during Credit Review|
|T12|QUESTIONNAIRE_PENDING|QUESTIONNAIRE_DRAFT|Save Questionnaire as Draft|R1|- Enter questionnaire information<br>- Save as draft (not visible to others)|Yes|Front Office saves partial work on questionnaire|
|T13|QUESTIONNAIRE_DRAFT|QUESTIONNAIRE_PENDING|Continue Editing Questionnaire|R1|- Resume editing draft questionnaire|Yes|Front Office returns to edit existing draft|
|T14|QUESTIONNAIRE_DRAFT|QUESTIONNAIRE_PENDING|Publish Questionnaire to Credit Paper|R1|- Make final edits<br>- Publish to make visible to all parties|No|Questionnaire becomes visible to all authorized users|
|T15|QUESTIONNAIRE_PENDING|CREDIT_PAPER_COMPILATION|Complete Credit Questionnaire|R1|- Complete final questionnaire<br>- Submit completed questionnaire|No|Front Office provides detailed information about the counterparty's business|
|T16|CREDIT_ANALYSIS_IN_PROGRESS|CREDIT_ANALYSIS_DRAFT|Save Analysis as Draft|R2, R3-R8|- Enter credit analysis information<br>- Save as draft (not visible to others)|Yes|Credit Analyst saves partial work on analysis|
|T17|CREDIT_ANALYSIS_DRAFT|CREDIT_ANALYSIS_IN_PROGRESS|Continue Editing Analysis|R2, R3-R8|- Resume editing draft analysis|Yes|Credit Analyst returns to edit existing draft|
|T18|CREDIT_ANALYSIS_DRAFT|CREDIT_ANALYSIS_IN_PROGRESS|Publish Analysis to Credit Paper|R2, R3-R8|- Make final edits<br>- Publish to make visible to all parties|No|Analysis becomes visible to all authorized users|
|T19|CREDIT_ANALYSIS_IN_PROGRESS|CREDIT_PAPER_COMPILATION|Complete Credit Analysis|R2, R3-R8|- Complete all required sections of the Credit Analysis<br>- Upload supporting financial analysis<br>- Make credit recommendation|No|Credit Analysis completed and ready for inclusion in final Credit Paper|
|T20|LEGAL_REVIEW_IN_PROGRESS|LEGAL_REVIEW_DRAFT|Save Legal Review as Draft|R11|- Enter legal review information<br>- Save as draft (not visible to others)|Yes|Legal Reviewer saves partial work on review|
|T21|LEGAL_REVIEW_DRAFT|LEGAL_REVIEW_IN_PROGRESS|Continue Editing Legal Review|R11|- Resume editing draft legal review|Yes|Legal Reviewer returns to edit existing draft|
|T22|LEGAL_REVIEW_DRAFT|LEGAL_REVIEW_IN_PROGRESS|Publish Legal Review to Credit Paper|R11|- Make final edits<br>- Publish to make visible to all parties|No|Legal Review becomes visible to all authorized users|
|T23|LEGAL_REVIEW_IN_PROGRESS|CREDIT_PAPER_COMPILATION|Complete Legal Review|R11|- Document legal terms and conditions<br>- Identify any legal risks<br>- Provide legal opinion|No|Legal Review is completed and added to the Credit Paper|
|T24|CREDIT_PAPER_COMPILATION|APPROVAL_PENDING_INDIVIDUAL|Submit for Individual Approval|R2, R3-R8|- Finalize Credit Paper<br>- Route to appropriate individual approver based on DA level|No|For DA levels 3-8, individual approval is sufficient|
|T25|CREDIT_PAPER_COMPILATION|APPROVAL_PENDING_COMMITTEE|Submit for Committee Approval|R2, R3-R8|- Finalize Credit Paper<br>- Schedule committee review<br>- Distribute documents to committee members|No|For DA levels 1-2, committee approval is required|
|T26|APPROVAL_PENDING_INDIVIDUAL|APPROVED|Approve Credit Request|R3-R8|- Record approval decision<br>- Add any approval comments<br>- Generate final approved Credit Paper|No|Individual approver with appropriate DA level approves the request|
|T27|APPROVAL_PENDING_COMMITTEE|APPROVED|Approve by Committee|R9|- Upload committee minutes<br>- Record approval decision<br>- Add any committee comments<br>- Generate final approved Credit Paper|No|Committee approval is documented with meeting minutes|
|T28|APPROVAL_PENDING_INDIVIDUAL|REJECTED|Reject Credit Request|R3-R8|- Record rejection decision<br>- Provide rejection reason<br>- Add comments explaining decision|No|Individual approver rejects the request|
|T29|APPROVAL_PENDING_COMMITTEE|REJECTED|Reject by Committee|R9|- Upload committee minutes<br>- Record rejection decision<br>- Provide rejection reason<br>- Add committee comments|No|Committee rejects the request|
|T30|APPROVAL_PENDING_INDIVIDUAL|RETURNED_TO_CREDIT_ANALYSIS|Return for Further Analysis|R3-R8|- Specify additional analysis required<br>- Add comments for Credit Analyst|No|Used when approver requires more information or analysis before making a decision|
|T31|APPROVAL_PENDING_COMMITTEE|RETURNED_TO_CREDIT_ANALYSIS|Return for Further Analysis|R9|- Specify additional analysis required<br>- Add committee comments|No|Committee requires more information or analysis|
|T32|RETURNED_TO_CREDIT_ANALYSIS|CREDIT_ANALYSIS_IN_PROGRESS|Resume Credit Analysis|R2, R3-R8|- Acknowledge return comments<br>- Begin additional analysis|No|Credit Analyst resumes work based on approver feedback|

|T34|ANY STATE|CANCELLED|Cancel Credit Request|R1, R12|- Provide cancellation reason<br>- Record cancellation details|No|Request can be cancelled by Front Office or System Administrator at any point|

## 4. Parallel Processing Model

The Credit Risk Workflow includes parallel processing paths that begin **only after** Business Sponsorship approval:

1. **Main Path**: Business Sponsorship Approved → Credit Analysis → Credit Paper Compilation
2. **Legal Path**: Business Sponsorship Approved → Legal Review → Credit Paper Compilation
3. **Questionnaire Path** (if required): Business Sponsorship Approved → Questionnaire Pending → Credit Analysis → Credit Paper Compilation

These paths converge at the Credit Paper Compilation stage before proceeding to approval. It's important to note that Credit Analysis, Legal Review, and Credit Questionnaire processes do NOT start while Business Sponsorship is pending - they begin only after the Business Sponsor has approved the request.

## 5. Draft Management

Each of the three parallel processes supports draft management capabilities, allowing preparers to work privately on their components before sharing with others.

### 5.1 Draft Management Model

|Component|Draft State|Main State|Publication Process|Visibility Rules|
|---|---|---|---|---|
|Credit Questionnaire|QUESTIONNAIRE_DRAFT|QUESTIONNAIRE_PENDING|Explicit "Publish to Credit Paper" action|Draft visible only to Relationship Manager, Published visible to all authorized users|
|Legal Review|LEGAL_REVIEW_DRAFT|LEGAL_REVIEW_IN_PROGRESS|Explicit "Publish to Credit Paper" action|Draft visible only to Legal Reviewer, Published visible to all authorized users|
|Credit Analysis|CREDIT_ANALYSIS_DRAFT|CREDIT_ANALYSIS_IN_PROGRESS|Explicit "Publish to Credit Paper" action|Draft visible only to Credit Analyst, Published visible to all authorized users|

### 5.2 Draft Management Actions

|Action|Description|Performed By|Effect|
|---|---|---|---|
|Save as Draft|Saves the current state of work without making it visible to other parties|Document preparer|Updates stored in system but only visible to the creator|
|Save to Credit Paper|Finalizes current section and makes it visible to all parties with Credit Paper access|Document preparer|Updates visible to all authorized users in the Credit Paper|
|Revert to Draft|Takes a previously saved section back to draft status for further edits|Document preparer|Section becomes private again until next "Save to Credit Paper"|

### 5.3 Component Visualization in Credit Paper

When a component is published through the "Save to Credit Paper" action:

- The content becomes immediately visible in the assembled Credit Paper
- All authorized users can see the latest published version
- The component preparer can continue working on new drafts
- Each publication creates a new version in the system's history

### 5.4 Draft State Workflow Patterns

Each component follows this pattern for draft management:

```
MAIN_STATE → DRAFT_STATE → MAIN_STATE (with published content)
```

During the workflow, a component can cycle between its main state and draft state multiple times, with each publication creating a new version visible in the Credit Paper.

## 6. State Transition Rules and Validations

### 6.1 Required Data by Transition

|Transition|Required Data Validation|
|---|---|
|T1: DRAFT → SUBMITTED|- All required Credit Limit Application fields<br>- At least one Credit Limit entry<br>- Valid CounterParty information<br>- Valid Business Sponsor selection|
|T5: CREDIT_REVIEW → ASSIGNED_DA_LEVEL|- Valid DA level (1-8)<br>- Credit Questionnaire requirement flag<br>- Assigned Credit Analyst|
|T7: BUSINESS_SPONSORSHIP_PENDING → BUSINESS_SPONSOR_APPROVED|- Business Sponsor approval comments<br>- Business Sponsor approval timestamp|
|T14: QUESTIONNAIRE_DRAFT → QUESTIONNAIRE_PENDING|- Publication note explaining changes<br>- Minimum required questionnaire fields completed|
|T18: CREDIT_ANALYSIS_DRAFT → CREDIT_ANALYSIS_IN_PROGRESS|- Publication note explaining changes<br>- Minimum required analysis fields completed|
|T22: LEGAL_REVIEW_DRAFT → LEGAL_REVIEW_IN_PROGRESS|- Publication note explaining changes<br>- Minimum required legal review fields completed|
|T19: CREDIT_ANALYSIS_IN_PROGRESS → CREDIT_PAPER_COMPILATION|- Complete Credit Analysis with all required sections<br>- Credit recommendation<br>- Financial analysis|
|T23: LEGAL_REVIEW_IN_PROGRESS → CREDIT_PAPER_COMPILATION|- Complete Legal Review with agreement analysis<br>- Legal opinion on documentation|
|T26/T27: APPROVAL_PENDING → APPROVED|- Approval decision record<br>- Appropriate authority level confirmation|

### 6.2 State Duration Monitoring

|State|Expected Duration|Warning Threshold|Escalation Threshold|
|---|---|---|---|
|SUBMITTED|1 business day|2 business days|3 business days|
|CREDIT_REVIEW|2 business days|3 business days|5 business days|

|BUSINESS_SPONSORSHIP_PENDING|2 business days|3 business days|5 business days|
|QUESTIONNAIRE_PENDING|3 business days|5 business days|7 business days|
|CREDIT_ANALYSIS_IN_PROGRESS|5 business days|7 business days|10 business days|
|LEGAL_REVIEW_IN_PROGRESS|5 business days|7 business days|10 business days|
|APPROVAL_PENDING_INDIVIDUAL|2 business days|3 business days|5 business days|
|APPROVAL_PENDING_COMMITTEE|5 business days|7 business days|10 business days|

_Note: Draft states do not have duration monitoring as they are considered transient states within their parent state's timeline._

### 6.3 Priority Impact on State Duration

|Priority|Duration Modifier|
|---|---|
|Low|Standard duration|
|Medium|75% of standard duration|
|High|50% of standard duration|

## 7. Workflow Visualizations

### 7.1 Primary Workflow Path with Draft States

```
DRAFT → SUBMITTED → CREDIT_REVIEW → BUSINESS_SPONSORSHIP_PENDING
→ BUSINESS_SPONSOR_APPROVED → [PARALLEL PROCESSES WITH DRAFT STATES] → CREDIT_PAPER_COMPILATION 
→ APPROVAL_PENDING → APPROVED/REJECTED
```

### 7.2 Parallel Processes with Draft States

```
1. BUSINESS_SPONSOR_APPROVED → CREDIT_ANALYSIS_IN_PROGRESS ↔ CREDIT_ANALYSIS_DRAFT → CREDIT_PAPER_COMPILATION
2. BUSINESS_SPONSOR_APPROVED → LEGAL_REVIEW_IN_PROGRESS ↔ LEGAL_REVIEW_DRAFT → CREDIT_PAPER_COMPILATION
3. BUSINESS_SPONSOR_APPROVED → QUESTIONNAIRE_PENDING ↔ QUESTIONNAIRE_DRAFT → CREDIT_PAPER_COMPILATION
```

### 7.3 Rejection Paths

```
BUSINESS_SPONSORSHIP_PENDING → REJECTED
APPROVAL_PENDING → RETURNED_TO_CREDIT_ANALYSIS → CREDIT_ANALYSIS_IN_PROGRESS
APPROVAL_PENDING → REJECTED
```

### 7.4 Additional Information Path

```

```

## 8. Special Handling Notes

### 8.1 Business Sponsorship Gate

- Business Sponsorship approval is a mandatory gate before any further processing
- Credit Analysis, Legal Review, and Credit Questionnaire processes ONLY begin after Business Sponsor approval
- This ensures senior stakeholder support before investing resources in detailed analysis

### 8.2 Draft State Management

- Draft states are private working states only visible to the creator
- Multiple draft versions can be saved before publishing
- Publication is an explicit action that makes content visible to others
- The system maintains version history of both drafts and published versions
- Draft states are not part of the main workflow path for reporting purposes

### 8.3 Concurrent Editing Protection

- Document locking prevents multiple users from editing the same component simultaneously
- Locks automatically expire after a configurable period (default: 30 minutes of inactivity)
- Users can request lock override in emergency situations (requires System Administrator role)
- Lock status is visually indicated in the UI

### 8.4 Draft vs. Published Content Visibility

- Draft content is only visible to its creator
- Published content is visible to all authorized users based on their roles
- The latest published version of each component appears in the Credit Paper
- Users cannot modify published content directly - they must create a new draft
- Each publication requires a note explaining the changes made

### 8.5 High Priority Requests

- High priority requests will receive visual highlighting in dashboards
- Automated notifications will be more frequent for approaching thresholds
- High priority requests require justification and additional Business Sponsor approval

### 8.6 Legal Documentation Complexity

- Complex legal structures may result in extended Legal Review periods
- For complex cases, the Legal Review may include multiple Legal Reviewers
- The system should support "partial saves" of Legal Review drafts

### 8.7 Committee Approval Process

- Committee approvals (DA1-DA2) require scheduling coordination
- System should support uploading of committee minutes
- Multiple committee members may need to indicate approval

### 8.8 DA Level Determination Factors

- DA level is determined based on risk assessment, exposure amount, and counterparty risk
- Higher risk requests are assigned lower DA numbers (DA1-DA2) requiring committee approval
- Lower risk requests are assigned higher DA numbers (DA3-DA8) allowing individual approval

### 8.9 Parallel Process Synchronization

- The system must track completion status of parallel paths (Credit Analysis, Legal Review, Credit Questionnaire)
- Credit Paper Compilation can only begin when all required parallel paths are complete
- Status dashboards should clearly indicate which parallel paths are pending

### 8.10 Document Version Control

- All documents attached during the workflow should maintain version history
- Final approved Credit Papers should be marked as final with appropriate security controls
- Document access should be restricted based on workflow state and user role

### 8.11 User Interface Requirements for Draft Management

- Clear visual distinction between draft and published states
- Explicit "Save as Draft" and "Publish to Credit Paper" buttons
- Warning when navigating away from unsaved drafts
- Version comparison capability
- Publication note requirement for context