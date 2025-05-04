


ah I see now. If you review the Product Requirements Document (PRD.md) in the requirements folder you will see that after business approval the Credit Request kicks off 3 parallel processes:

Credit Questionnaire (only required in certain circumstances)
Legal Review
Credit Analysis

Each of these three sub-processes can run independently so whilst the overall Credit Request is still in Business_Sponsorship_Approved state, the sub-processes should have also been stated, each with their own state - in this case Questionnaire_Draft...and when the Questionnaire is submitted then this sub-process should be transitioned to Questionnaire_Complete (although this state does not yet existing in the model)

I think there needs to be a change to the state transition model to distinguish between the overall Credit Paper which is the "parent process" and then sub-processes for each of the individual forms that make up different parts of the overall Credit Paper, specifically:
- Credit Request
- Credit Review
- Business Sponsorship
- Credit Questionnaire
- Legal Review
- Credit Analysis
- Credit Paper Compilation
- Credit Approval

Phase 1: Credit Request phase:
The relationship manager initiates a Credit Request.  This will create:
CREDIT_PAPER_CREDIT_REQUEST - parent process state
CREDIT_REQUEST_DRAFT - Credit Request sub-process state

Relationship manager can edit this Credit Request during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Request form in CREDIT_REQUEST_IN_PROGRESS state.  This version of the Credit Request form is used to update the Credit Paper detailed form when viewed. The relationship manager can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the relationship manager will submit the Credit Request form for Credit Review ("Submit for Credit Review") at which point the Credit Request sub-process moved to CREDIT_REQUEST_SUBMITTED state 

The Credit Paper parent process then moves to Credit Review phase.

Phase 2: Credit Review phase:
The credit analyst own this phase. Once the Credit Paper moves to the Credit Review phase the Credit Paper moves to the next state:
CREDIT_PAPER_CREDIT_REVIEW_PENDING - parent process state
The Credit Paper can be viewed by a Credit Analyst the edit button will be available.  Once the credit analyst clicks on this edit button for the first time, the Credit Review sub-process is initiated and this will create:
CREDIT_REVIEW_DRAFT - Credit Review sub-process state.

The credit analyst can edit this Credit Review during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Review form in CREDIT_REVIEW_IN_PROGRESS state.  This version of the Credit Review form is used to update the Credit Paper detailed form when viewed. The credit analyst can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the credit analyst will submit the Credit Review form for Business Sponsorship ("Submit for Business Sponsorship") at which point the Credit Review sub-process moves to CREDIT_REVIEW_SUBMITTED state.

The Credit Paper parent process then moves to Business Sponsorship phase.

Phase 3: Business Sponsorship phase:
The business sponsor owns this phase. Once the Credit Paper moves to the Business Sponsorship phase the Credit Paper moves to the next state:
CREDIT_PAPER_BUSINESS_SPONSOR_PENDING - parent process state
The Credit Paper can be viewed by a business sponsor and the edit button will be available.  Once the business sponsor clicks on this edit button for the first time, the Business Sponsorship sub-process is initiated and this will create:
BUSINESS_SPONSOR_DRAFT - Business Sponsorship sub-process state.

The business sponsor can edit this Business Sponsorship form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Business Sponsorship form in BUSINESS_SPONSOR_IN_PROGRESS state.  This version of the Business Sponsorship form is used to update the Credit Paper detailed form when viewed. The business sponsor can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the business sponsor will submit the Business Sponsorship form for detailed analysis ("Submit for Analysis") at which point the Business Sponsorship sub-process moves to BUSINESS_SPONSOR_SUBMITTED state.

The Credit Paper parent process then moves to analysis phase.

Phase 4: Analysis phase:
In the analysis phase there are 3 separate parallel sub-processes that are initiated simultaneously:
- Credit Questionnaire
- Legal Review
- Credit Analysis

Once the Credit Paper moves to the analysis phase the Credit Paper moves to the next state:
CREDIT_PAPER_ANALYSIS_PENDING - parent process state

Phase 4a: Credit Questionnaire
The relationship manager is responsible for completing the Credit Questionnaire if required.
During the Credit Review phase, one of the fields required to be completed is whether a Credit Questionnaire is required. If this is "ticked", then the Credit Questionnaire sub-process will be initiated once the Credit Paper reaches analysis phase.

The Credit Paper can be viewed by a relationship manager and the edit button will be available if the questionnaire required box is ticked on the credit paper.  Once the relationship manager clicks on this edit button for the first time, the Credit Questionnaire sub-process is initiated and this will create:
CREDIT_QUESTIONNAIRE_DRAFT - Credit questionnaire sub-process state.

The relationship manager can edit this Credit Questionnaire form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Questionnaire form in CREDIT_QUESTIONNAIRE_IN_PROGRESS state.  This version of the Credit Questionnaire form is used to update the Credit Paper detailed form when viewed. The relationship manager can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the relationship manager will submit the Credit Questionnaire form for review ("Submit for Review") at which point the Credit Questionnaire sub-process moves to CREDIT_QUESTIONNAIRE_SUBMITTED state.

The Credit Paper parent process can only moves to Credit Compilation phase if the other two parallel processes have been completed. if not, then the Credit Paper will continue to remain in CREDIT_PAPER_ANALYSIS_PENDING state.

Phase 4b: Legal Review
The legal reviewer is responsible for completing the Legal Review.
The legal review sub-process will be initiated once the Credit Paper reaches analysis phase.

The Credit Paper can be viewed by a legal reviewer and the edit button will be available.  Once the legal reviewer clicks on this edit button for the first time, the Legal Review sub-process is initiated and this will create:
LEGAL_REVIEW_DRAFT - Legal review sub-process state.

The legal reviewer can edit this Legal Review form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Legal Review form in LEGAL_REVIEW_IN_PROGRESS state.  This version of the Legal Review form is used to update the Credit Paper detailed form when viewed. The legal reviewer can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the legal reviewer will submit the Legal Review form for review ("Submit for Review") at which point the Legal Review sub-process moves to LEGAL_REVIEW_SUBMITTED state.

The Credit Paper parent process can only move to Credit Compilation phase if the other two parallel processes have been completed. if not, then the Credit Paper will continue to remain in CREDIT_PAPER_ANALYSIS_PENDING state.

Phase 4c: Credit Analysis
The assigned credit analyst is responsible for completing the credit analysis. During the Credit Review phase a specific credit analyst is assigned to complete this form.
The credit analysis sub-process will be initiated once the Credit Paper reaches analysis phase.

The Credit Paper can be viewed by a credit analyst and the edit button will be available.  Once the credit analyst clicks on this edit button for the first time, the Credit Analysis sub-process is initiated and this will create:
CREDIT_ANALYSIS_DRAFT - Credit analysis sub-process state.

The credit analyst can edit this Credit Analysis form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Analysis form in CREDIT_ANALYSIS_IN_PROGRESS state.  This version of the Credit Analysis form is used to update the Credit Paper detailed form when viewed. The credit analyst can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the credit analyst will submit the Credit Analysis form for review ("Submit for Review") at which point the Credit Analysis sub-process moves to CREDIT_ANALYSIS_SUBMITTED state.

The Credit Paper parent process can only move to Credit Compilation phase if the other two parallel processes have been completed. if not, then the Credit Paper will continue to remain in CREDIT_PAPER_ANALYSIS_PENDING state.

Once all 3 parallel processes have been submitted then the Credit Paper parent process can move to Credit Compilation phase. In practice the Credit Questionnaire and Legal Review would alway be completed prior to the Credit Analysis and hence a an implementation of the state transition would operate on the Credit Analysis sub-process to trigger the parent process to move to the next phase with the check that both the Legal Review and Credit Questionnaire sub processes were also in a submitted state.  The Credit Paper process would then progress to:
CREDIT_PAPER_COMPILATION state.

Phase 5: Credit Paper compilation
The assigned credit analyst is responsible for completing the credit compilation phase. 
The credit compilation sub-process will be initiated once the Credit Paper reaches Credit paper compilation phase.

The Credit Paper can be viewed by a credit analyst and the edit button will be available.  Once the credit analyst clicks on this edit button for the first time, the Credit Compilation sub-process is initiated and this will create:
CREDIT_COMPILATION_DRAFT - Credit compilation sub-process state.

The credit analyst can edit this Credit Compilation form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Compilation form in CREDIT_COMPILATION_IN_PROGRESS state.  This version of the Credit Compilation form is used to update the Credit Paper detailed form when viewed. The credit analyst can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the credit analyst will submit the Credit Compilation form for approval ("Submit for Approval") at which point the Credit Compilation sub-process moves to CREDIT_COMPILATION_SUBMITTED state.

The Credit Paper parent process then moves to approval phase.

Phase 6: Credit Paper Approval phase:
This stage of the process is owned by the approver (being a credit analyst with specific DA approval level or a credit analyst that has been set up as the committee approver and will facilitate attaching the minutes of the committee approval), they are responsible for completing this phase.

The Credit Paper can be viewed by an approver and the edit button will be available.  Once the approver clicks on this edit button for the first time, the Credit Approval sub-process is initiated and this will create:
CREDIT_APPROVAL_DRAFT - Credit approval sub-process state.

The approver can edit this Credit Approval form during this phase as many time as they wish.  Each time they edit they can save their changes as Draft ("Save as Draft"), or they can Submit change to the Credit Paper ("Update Credit Paper"), creating a second version of the Credit Approval form in CREDIT_APPROVAL_IN_PROGRESS state.  This version of the Credit Approval form is used to update the Credit Paper detailed form when viewed. The approver can continue to make edits in the Draft state and can continue to Submit changes to the In Progress state as many time as they wish.

Once completed, the approver will submit the Credit Approval form for approval or rejection ("Submit for Approval" or "Submit Rejection") at which point the Credit Approval sub-process moves to CREDIT_APPROVAL_SUBMITTED state.

The Credit Paper parent process then moves to its final state, either:
CREDIT_PAPER_APPROVED, or
CREDIT_PAPER_REJECTED







