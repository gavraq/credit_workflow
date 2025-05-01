from django.core.management.base import BaseCommand
from workflow.models import WorkflowState, WorkflowStateTransition

# List of workflow states from State Machine Model - Credit Workflow (FINAL).md
STATES = [
    {"state_id": "S1", "name": "DRAFT", "description": "Initial state when a credit request is being created but not yet submitted", "is_initial": True, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S2", "name": "SUBMITTED", "description": "Credit limit application has been submitted by Front Office", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S3", "name": "CREDIT_REVIEW", "description": "Credit Risk is reviewing the application", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},

    {"state_id": "S6", "name": "BUSINESS_SPONSORSHIP_PENDING", "description": "Awaiting approval from Business Sponsor", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S7", "name": "BUSINESS_SPONSOR_APPROVED", "description": "Business Sponsor has approved, parallel processes can begin", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S8", "name": "CREDIT_ANALYSIS_IN_PROGRESS", "description": "Credit Analysis being performed by Credit Analyst", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S8D", "name": "CREDIT_ANALYSIS_DRAFT", "description": "Credit Analysis being drafted (private to Credit Analyst)", "is_initial": False, "is_final": False, "is_draft_state": True, "parent_state": "S8"},
    {"state_id": "S9", "name": "LEGAL_REVIEW_IN_PROGRESS", "description": "Legal Review being performed by Legal Reviewer", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S9D", "name": "LEGAL_REVIEW_DRAFT", "description": "Legal Review being drafted (private to Legal Reviewer)", "is_initial": False, "is_final": False, "is_draft_state": True, "parent_state": "S9"},
    {"state_id": "S10", "name": "QUESTIONNAIRE_PENDING", "description": "Credit Questionnaire required and pending from Front Office", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S10D", "name": "QUESTIONNAIRE_DRAFT", "description": "Credit Questionnaire being drafted (private to Front Office)", "is_initial": False, "is_final": False, "is_draft_state": True, "parent_state": "S10"},
    {"state_id": "S11", "name": "CREDIT_PAPER_COMPILATION", "description": "All components being compiled into final Credit Paper", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S12", "name": "APPROVAL_PENDING_INDIVIDUAL", "description": "Awaiting individual approval (DA3-DA8)", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S13", "name": "APPROVAL_PENDING_COMMITTEE", "description": "Awaiting committee approval (DA1-DA2)", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
    {"state_id": "S14", "name": "APPROVED", "description": "Credit request has been approved", "is_initial": False, "is_final": True, "is_draft_state": False, "parent_state": None},
    {"state_id": "S15", "name": "REJECTED", "description": "Credit request has been rejected", "is_initial": False, "is_final": True, "is_draft_state": False, "parent_state": None},
    {"state_id": "S16", "name": "CANCELLED", "description": "Credit request has been cancelled", "is_initial": False, "is_final": True, "is_draft_state": False, "parent_state": None},

    {"state_id": "S18", "name": "RETURNED_TO_CREDIT_ANALYSIS", "description": "Credit request returned to Credit Analysis for revision", "is_initial": False, "is_final": False, "is_draft_state": False, "parent_state": None},
]

# List of all transitions from State Machine Model - Credit Workflow (FINAL).md
TRANSITIONS = [
    {"transition_id": "T1", "from_state": "S1", "to_state": "S2", "name": "Submit Application", "required_roles": "R1", "actions_required": "Complete all required fields in Credit Limit Application; Attach any initial supporting documents", "is_draft_action": False, "notes": "Front Office submits the initial request, which must include counterparty details, proposed limits, and business rationale"},
    {"transition_id": "T2", "from_state": "S2", "to_state": "S3", "name": "Begin Credit Review", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Assign request to specific Credit Analyst; Initial review of application completeness", "is_draft_action": False, "notes": "Credit Risk department takes ownership of the request and begins initial assessment"},

    {"transition_id": "T7", "from_state": "S6", "to_state": "S7", "name": "Approve as Business Sponsor", "required_roles": "R10", "actions_required": "Provide approval with comments; Record date of approval", "is_draft_action": False, "notes": "Business Sponsor confirms support for the credit request"},
    {"transition_id": "T8", "from_state": "S6", "to_state": "S15", "name": "Reject as Business Sponsor", "required_roles": "R10", "actions_required": "Provide rejection reason; Add comments explaining decision", "is_draft_action": False, "notes": "Business Sponsor does not support the request"},
    {"transition_id": "T9", "from_state": "S7", "to_state": "S8", "name": "Begin Credit Analysis", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Start detailed credit analysis; Gather financial data", "is_draft_action": False, "notes": "Credit Analysis begins only after Business Sponsor approval"},
    {"transition_id": "T10", "from_state": "S7", "to_state": "S9", "name": "Begin Legal Review", "required_roles": "R11", "actions_required": "Start legal documentation analysis", "is_draft_action": False, "notes": "Legal Review begins only after Business Sponsor approval"},
    {"transition_id": "T11", "from_state": "S7", "to_state": "S10", "name": "Request Credit Questionnaire", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Mark Credit Questionnaire as required; Notify Front Office", "is_draft_action": False, "notes": "Only triggered if Credit Questionnaire was required during Credit Review"},
    {"transition_id": "T12", "from_state": "S10", "to_state": "S10D", "name": "Save Questionnaire as Draft", "required_roles": "R1", "actions_required": "Enter questionnaire information; Save as draft (not visible to others)", "is_draft_action": True, "notes": "Front Office saves partial work on questionnaire"},
    {"transition_id": "T13", "from_state": "S10D", "to_state": "S10", "name": "Continue Editing Questionnaire", "required_roles": "R1", "actions_required": "Resume editing draft questionnaire", "is_draft_action": True, "notes": "Front Office returns to edit existing draft"},
    {"transition_id": "T14", "from_state": "S10D", "to_state": "S10", "name": "Publish Questionnaire to Credit Paper", "required_roles": "R1", "actions_required": "Make final edits; Publish to make visible to all parties", "is_draft_action": False, "notes": "Questionnaire becomes visible to all authorized users"},
    {"transition_id": "T15", "from_state": "S10", "to_state": "S11", "name": "Complete Credit Questionnaire", "required_roles": "R1", "actions_required": "Complete final questionnaire; Submit completed questionnaire", "is_draft_action": False, "notes": "Front Office provides detailed information about the counterparty's business"},
    {"transition_id": "T16", "from_state": "S8", "to_state": "S8D", "name": "Save Analysis as Draft", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Enter credit analysis information; Save as draft (not visible to others)", "is_draft_action": True, "notes": "Credit Analyst saves partial work on analysis"},
    {"transition_id": "T17", "from_state": "S8D", "to_state": "S8", "name": "Continue Editing Analysis", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Resume editing draft analysis", "is_draft_action": True, "notes": "Credit Analyst returns to edit existing draft"},
    {"transition_id": "T18", "from_state": "S8D", "to_state": "S8", "name": "Publish Analysis to Credit Paper", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Make final edits; Publish to make visible to all parties", "is_draft_action": False, "notes": "Analysis becomes visible to all authorized users"},
    {"transition_id": "T19", "from_state": "S8", "to_state": "S11", "name": "Complete Credit Analysis", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Complete all required sections of the Credit Analysis; Upload supporting financial analysis; Make credit recommendation", "is_draft_action": False, "notes": "Credit Analysis completed and ready for inclusion in final Credit Paper"},
    {"transition_id": "T20", "from_state": "S9", "to_state": "S9D", "name": "Save Legal Review as Draft", "required_roles": "R11", "actions_required": "Enter legal review information; Save as draft (not visible to others)", "is_draft_action": True, "notes": "Legal Reviewer saves partial work on review"},
    {"transition_id": "T21", "from_state": "S9D", "to_state": "S9", "name": "Continue Editing Legal Review", "required_roles": "R11", "actions_required": "Resume editing draft legal review", "is_draft_action": True, "notes": "Legal Reviewer returns to edit existing draft"},
    {"transition_id": "T22", "from_state": "S9D", "to_state": "S9", "name": "Publish Legal Review to Credit Paper", "required_roles": "R11", "actions_required": "Make final edits; Publish to make visible to all parties", "is_draft_action": False, "notes": "Legal Review becomes visible to all authorized users"},
    {"transition_id": "T23", "from_state": "S9", "to_state": "S11", "name": "Complete Legal Review", "required_roles": "R11", "actions_required": "Document legal terms and conditions; Identify any legal risks; Provide legal opinion", "is_draft_action": False, "notes": "Legal Review is completed and added to the Credit Paper"},
    {"transition_id": "T24", "from_state": "S11", "to_state": "S12", "name": "Submit for Individual Approval", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Finalize Credit Paper; Route to appropriate individual approver based on DA level", "is_draft_action": False, "notes": "For DA levels 3-8, individual approval is sufficient"},
    {"transition_id": "T25", "from_state": "S11", "to_state": "S13", "name": "Submit for Committee Approval", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Finalize Credit Paper; Schedule committee review; Distribute documents to committee members", "is_draft_action": False, "notes": "For DA levels 1-2, committee approval is required"},
    {"transition_id": "T26", "from_state": "S12", "to_state": "S14", "name": "Approve Credit Request", "required_roles": "R3,R4,R5,R6,R7,R8", "actions_required": "Record approval decision; Add any approval comments; Generate final approved Credit Paper", "is_draft_action": False, "notes": "Individual approver with appropriate DA level approves the request"},
    {"transition_id": "T27", "from_state": "S13", "to_state": "S14", "name": "Approve by Committee", "required_roles": "R9", "actions_required": "Upload committee minutes; Record approval decision; Add any committee comments; Generate final approved Credit Paper", "is_draft_action": False, "notes": "Committee approval is documented with meeting minutes"},
    {"transition_id": "T28", "from_state": "S12", "to_state": "S15", "name": "Reject Credit Request", "required_roles": "R3,R4,R5,R6,R7,R8", "actions_required": "Record rejection decision; Provide rejection reason; Add comments explaining decision", "is_draft_action": False, "notes": "Individual approver rejects the request"},
    {"transition_id": "T29", "from_state": "S13", "to_state": "S15", "name": "Reject by Committee", "required_roles": "R9", "actions_required": "Upload committee minutes; Record rejection decision; Provide rejection reason; Add committee comments", "is_draft_action": False, "notes": "Committee rejects the request"},
    {"transition_id": "T30", "from_state": "S12", "to_state": "S18", "name": "Return for Further Analysis", "required_roles": "R3,R4,R5,R6,R7,R8", "actions_required": "Specify additional analysis required; Add comments for Credit Analyst", "is_draft_action": False, "notes": "Used when approver requires more information or analysis before making a decision"},
    {"transition_id": "T31", "from_state": "S13", "to_state": "S18", "name": "Return for Further Analysis", "required_roles": "R9", "actions_required": "Specify additional analysis required; Add committee comments", "is_draft_action": False, "notes": "Committee requires more information or analysis"},
    {"transition_id": "T32", "from_state": "S18", "to_state": "S8", "name": "Resume Credit Analysis", "required_roles": "R2,R3,R4,R5,R6,R7,R8", "actions_required": "Acknowledge return comments; Begin additional analysis", "is_draft_action": False, "notes": "Credit Analyst resumes work based on approver feedback"},

    # Explicit cancel transitions for each non-final state (except CANCELLED itself) will be added below
]

# Dynamically add a Cancel transition from every non-final state (except CANCELLED itself)
CANCEL_TRANSITION_TEMPLATE = {
    "name": "Cancel Credit Request",
    "required_roles": "R1,R12",
    "actions_required": "Provide cancellation reason; Record cancellation details",
    "is_draft_action": False,
    "notes": "Request can be cancelled by Front Office or System Administrator at any point"
}

final_state_ids = {s["state_id"] for s in STATES if s["is_final"] or s["state_id"] == "S16"}
non_final_states = [s for s in STATES if s["state_id"] not in final_state_ids]

for idx, state in enumerate(non_final_states, start=100):
    TRANSITIONS.append({
        "transition_id": f"TC{idx}",
        "from_state": state["state_id"],
        "to_state": "S16",
        **CANCEL_TRANSITION_TEMPLATE
    })


class Command(BaseCommand):
    help = "Load workflow states and transitions from the state machine model."

    def handle(self, *args, **options):
        # --- CLEANUP: Remove obsolete states and transitions ---
        from workflow.models import WorkflowState, WorkflowStateTransition
        from django.db.models import Q
        # Remove transitions not in TRANSITIONS
        valid_transition_ids = set(t["transition_id"] for t in TRANSITIONS)
        WorkflowStateTransition.objects.exclude(transition_id__in=valid_transition_ids).delete()
        # Remove states not in STATES
        valid_state_ids = set(s["state_id"] for s in STATES)
        WorkflowState.objects.exclude(state_id__in=valid_state_ids).delete()
        # --- NORMAL LOAD LOGIC ---
        state_objs = {}
        for state in STATES:
            parent = state_objs.get(state["parent_state"]) if state["parent_state"] else None
            obj, created = WorkflowState.objects.get_or_create(
                state_id=state["state_id"],
                defaults={
                    "name": state["name"],
                    "description": state["description"],
                    "is_initial": state["is_initial"],
                    "is_final": state["is_final"],
                    "is_draft_state": state["is_draft_state"],
                    "parent_state": parent
                }
            )
            state_objs[state["state_id"]] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created state: {obj}"))
            else:
                self.stdout.write(f"State already exists: {obj}")

        for trans in TRANSITIONS:
            from_state = state_objs[trans["from_state"]]
            to_state = state_objs[trans["to_state"]]
            obj, created = WorkflowStateTransition.objects.get_or_create(
                transition_id=trans["transition_id"],
                defaults={
                    "from_state": from_state,
                    "to_state": to_state,
                    "name": trans["name"],
                    "required_roles": trans["required_roles"],
                    "actions_required": trans["actions_required"],
                    "is_draft_action": trans["is_draft_action"],
                    "notes": trans["notes"],
                }
            )
            if not created:
                # Always update from_state and to_state if changed
                updated = False
                if obj.from_state != from_state:
                    obj.from_state = from_state
                    updated = True
                if obj.to_state != to_state:
                    obj.to_state = to_state
                    updated = True
                # Update other fields as well, if needed
                for field in ["name", "required_roles", "actions_required", "is_draft_action", "notes"]:
                    if getattr(obj, field) != trans[field]:
                        setattr(obj, field, trans[field])
                        updated = True
                if updated:
                    obj.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated transition: {obj}"))
                else:
                    self.stdout.write(f"Transition already exists and is up-to-date: {obj}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Created transition: {obj}"))
