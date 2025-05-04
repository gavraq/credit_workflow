

ok I have some suggestions and I would like you to revise the recommendation taking into account the proposed workflow outlined below.  There may be a number of changes required so I need you to make a detailed plan of steps required to achieve the proposed workflow.

## Credit Request
This stage of the process is owned by the relationship manager. They are going to create the request via the creditrequestwizard with the multi-form.
The Relationship Manager can "iterate" on this request as many times as they wish, each time saving as Draft until they are satisfied it is ready to submit or finally to send for Review. 
### Dashboard
If you are logged in as a Relationship Manager (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests submitted by the relationship manager including those that are in Draft state.
### Edit
When you edit a Credit Request it will open the edit request screen at:
`/credit-request/<id>/edit/` which will go to the wizard form at `/credit-request/wizard/`
### View
When you view a Credit Request it will open the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but 
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is still in  Draft state it will show as either Draft or Submitted state and all future states will simply show as not yet started.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which would take you to the edit request Credit Request screen.  Whilst still Draft any updates to this section is viewable only by the relationship manager making the request but once submitted it is available for all to see. 
- At this stage the Credit Review, Business Sponsorship, Credit Questionnaire, Legal Review and Credit Analysis and Documents Upload sections should show as not-started - at the top right of each section there should be and edit button but these are greyed out as the Credit Request has not progressed to these phases. 
- The Documents section should be its own section rather than the documents button previously seen in the actions section

Once you send the Credit Request for Review it progresses to the next phase.

### Credit Review
This stage of the process is owned by the credit analyst.  The credit analyst can see all requests that have at least reached the Submitted state
### Dashboard
If you are logged in as a Credit Analyst (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests in the Credit Review state including those that are in Draft state
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where assigned to a specific Credit Analyst filtered based on the logged in credit analyst
### Edit
When you click on a Credit Request that is in Credit Review state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Credit Review Form where you are able to complete the necessary sections and either save as Draft or Submit for Business Sponsorship
### View
When you click on a Credit Request that is in Credit Review state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Credit Review state the Credit Request phase will show as submitted, The Credit Review phase will show as in progress  and all future states will simply show as not yet started.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below.
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out as it is only editable by the relationship manager.
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should allow the Credit Analyst to take it into edit mode and edit the Credit Review form. Whilst still Draft any updates top this section are viewable only by the credit analyst but once submitted for business sponsorship it is available for all to see. 
- At this stage the Business Sponsorship, Credit Questionnaire, Legal Review and Credit Analysis and Documents Upload sections should show as not-started - at the top right of each section there should be and edit button but these are greyed out as the Credit Request has not progressed to these phases.
- The Documents section should be its own section rather than the documents button previously seen in the actions section

Once the Credit Review has been submitted it progresses to the next phase

### Business Sponsorship
This stage of the process is owned by the business sponsor.  The business sponsor can see all requests that have at least reached the Submitted for Business Sponsor state.
### Dashboard
If you are logged in as a Business Sponsor (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests in the awaiting business sponsorship state including those that are in Draft state
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where assigned to a specific Business Sponsor filtered based on the logged in Business Sponsor.
### Edit
When you click on a Credit Request that is in Awaiting Business Sponsorship state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Business Sponsorship Form where you are able to complete the necessary sections and either save as Draft or Submit for further processing (Questionnaire, Legal & Credit Analysis)
### View
When you click on a Credit Request that is in Awaiting Business Sponsorship state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Awaiting Business Sponsorship state the the Credit Request and Credit Review phases will show as submitted, The Awaiting Business Sponsorship phase will show as in progress  and all future states will simply show as not yet started.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out as it is only editable by the relationship manager
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should be greyed out as the business sponsor cannot edit this section
- The Business Sponsor section should have now have all of the fields from the Business Sponsorship form visible - in the top right there should be an edit button which should allow the Business Sponsor to take it into edit mode and edit the Business Sponsorship form.  Whilst still Draft any updates to this section are viewable only by the business sponsor but once submitted for further processing it is available for all to see. 
- At this stage the Credit Questionnaire, Legal Review and Credit Analysis and Documents Upload sections should show as not-started - on the top right of each section there should be and edit button but these are greyed out as the Credit Request has not progressed to these phases.
- The Documents section should be its own section rather than the documents button previously seen in the actions section

Once the Business Sponsorship has been submitted it progresses to the next phase for parallel processing

## Credit Questionnaire
If, during the Credit Review Phase the "requires Credit Questionnaire" has been ticked, then this process is started otherwise it is not applicable.

This stage of the process is owned by the relationship manager, they are responsible for completing the questionnaire.
### Dashboard
If you are logged in as a Relationship Manager (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests that require a questionnaire including those that are in Draft state.
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where a Credit Questionnaire is required based on the logged in user being the relationship manager requesting the Credit Request.
### Edit
When you click on a Credit Request that is in Questionnaire Pending state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Credit Questionnaire Form where you are able to complete the necessary sections and either save as Draft or Submit for further processing.
### View
When you click on a Credit Request that is in Questionnaire Pending state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Questionnaire Pending state the the Credit Request, Credit Review and Business Sponsorship phases will show as submitted, The Credit Questionnaire phase will show as in progress  and other parallel processing states will show their current status.  Other future states (eg approval) simply show as not yet started. 
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out as it has been submitted and approved from earlier states and is no longer editable by the relationship manager
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should be greyed out as the relationship manager cannot edit this section
- The Business Sponsor section should now have all of the fields from the Business Sponsor form visible - in the top right there should be an edit button which should be greyed out as the relationship manager cannot edit this section. 
- The Credit Questionnaire section should have now have all of the fields from the Credit Questionnaire form visible - in the top right there should be an edit button which should allow the relationship manager to take it into edit mode and edit the Credit Questionnaire form.  Whilst still Draft any updates to this section are viewable only by the relationship manager but once submitted for further processing it is available for all to see. 
- The Legal Review section should have now have all of the fields from the Legal Review form visible depending on whether the legal reviewer has started their review and submitted any updates - in the top right there should be an edit button which should be greyed out as the relationship manager cannot edit this section
- The Credit Analysis section should have now have all of the fields from the Credit Analysis form visible depending on whether the credit analyst has started their review and submitted any updates - in the top right there should be an edit button which should be greyed out as the relationship manager cannot edit this section
- The Documents Upload section should show any documents uploaded so far
- The Documents section should be its own section rather than the documents button previously seen in the actions section

### Legal Review
This stage of the process is owned by the legal reviewer, they are responsible for completing this section.
### Dashboard
If you are logged in as a Legal Reviewer (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests that have progressed to the Legal Review phase including those that are in Draft state.
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where a Legal Review is required based on the logged in user being a Legal Reviewer.
### Edit
When you click on a Credit Request that is in Legal Review state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Legal Review Form where you are able to complete the necessary sections and either save as Draft or Submit for further processing.
### View
When you click on a Credit Request that is in Legal Review state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Legal Review state the the Credit Request, Credit Review and Business Sponsorship phases will show as submitted, The Legal Review phase will show as in progress  and other parallel processing states will show their current status and other future states (eg approval) simply show as not yet started.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out as it is only editable by the relationship manager
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should be greyed out as the legal reviewer cannot edit this section
- The Business Sponsor section should now have all of the fields from the Business Sponsor form visible - in the top right there should be an edit button which should be greyed out as the legal reviewer cannot edit this section
- The Credit Questionnaire section should have now have all of the fields from the Credit Questionnaire form visible - in the top right there should be an edit button which should be greyed out as the legal reviewer cannot edit this section
- At this stage the Legal Review section should have now have all of the fields from the Legal Review form visible - in the top right there should be an edit button which should allow the legal reviewer to take it into edit mode and edit the Legal Review form.   Whilst still Draft any updates are viewable only by the legal reviewer but once submitted for further processing it is available for all to see. 
- The Credit Analysis section should have now have all of the fields from the Credit Analysis form visible depending on whether the credit analyst has started their review and submitted any updates - in the top right there should be an edit button which should be greyed out as the legal reviewer cannot edit this section
- The Documents Upload section should show any documents uploaded so far
- The Documents section should be its own section rather than the documents button previously seen in the actions section

## Credit Analysis
This stage of the process is owned by the assigned credit analyst, they are responsible for completing this section.
### Dashboard
If you are logged in as the assigned credit analyst (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests that have progressed to the Credit Analysis phase including those that are in Draft state.
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where a Credit analysis is required based on the logged in user being a the assigned credit analyst.
### Edit
When you click on a Credit Request that is in Credit analysis state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Credit analysis Form where you are able to complete the necessary sections and either save as Draft or Submit for further processing.
### View
When you click on a Credit Request that is in Credit analysis state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Credit analysis state the the Credit Request, Credit Review and Business Sponsorship phases will show as submitted, The Credit Analysis phase will show as in progress  and other parallel processing states will show their current status and other future states (eg approval) simply show as not yet started.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out as it is only editable by the relationship manager
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should be greyed out as the Credit Review can no longer be edited
- The Business Sponsor section should now have all of the fields from the Business Sponsor form visible - in the top right there should be an edit button which should be greyed out as the credit analyst cannot edit this section
- The Credit Questionnaire section should have now have all of the fields from the Credit Questionnaire form visible - in the top right there should be an edit button which should be greyed out as the credit analyst cannot edit this section
- At this stage the Legal Review section should have now have all of the fields from the Legal Review form visible - in the top right there should be an edit button which should be greyed out as the credit analyst cannot edit this section
- The Credit Analysis section should have now have all of the fields from the Credit Analysis form visible - in the top right there should be an edit button which should allow the credit analyst to take it into edit mode and edit the Credit Analysis form.  Whilst still Draft any updates to this section are viewable only by the assigned credit analyst but once submitted for further processing it is available for all to see. 
- The Documents Upload section should show any documents uploaded so far
- The Documents section should be its own section rather than the documents button previously seen in the actions section

Once all 3 of the parallel processes have been completed it progresses to Credit Paper compilation

## Credit Paper Compilation
This stage of the process is owned by the assigned credit analyst, they are responsible for completing this section.

In this phase all of the sections of the Credit Request Detail would have been completed in the previous section and are available for viewing and adding any final comments as well as preparing a PDF version of the form which can be printed out or emailed if required for any approvers.

Once the credit paper compilation is completed the credit analyst submits it for approval

## Approval
This stage of the process is owned by the approver (being a credit analyst with specific DA approval level or a credit analyst that has been set up as the committee approver and will facilitate attaching the minutes of the committee approval), they are responsible for completing this section.
### Dashboard
If you are logged in as an approver (or Admin) then the MyRequests page:
`/credit-request/` will show a list of all of the Credit Requests that have progressed to the Approval Pending phase.
The Assigned to me page (to be created but showing on the left navbar as a placeholder) will show all Credit Requests where a approval is required based on the logged in user being an approver with the requisite DA level or committee approver status.
### Edit
When you click on a Credit Request that is in Approval Pending state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the edit button it should take you to the Approval Form where you are able to complete the necessary sections and either approve or reject.
### View
When you click on a Credit Request that is in Approval Pending state from either the Dashboard screen, MyRequests screen or Assigned to me screen and click on the view button it should take you to the Credit Request Detail screen at :
`/credit-request/<id>/` - This screen has all sections of the final Credit Paper, but
- The Workflow Status section should have a horizontal progress bar with each of the phases showing with key dates for the state specifically started date and submitted date - when a Credit Request is in Approval Pending state the the Credit Request, Credit Review, Business Sponsorship, Credit Questionnaire, Legal Review and Credit Analysis phases will show as completed. The Approval phase will show as in progress.
- The current Actions section with the Edit and Documents buttons should be removed as it will be replaced as outlined below
- The Credit Request information should be shown next with each of the sub-sections per the wizard (Basic information, Limit Information, Relationship Information and Business Justification) - on the top right of the form there should be an Edit button which should be greyed out
- The Credit Review section should now have all of the fields from the Credit Review form visible - in the top right there should be an edit button which should be greyed out 
- The Business Sponsor section should now have all of the fields from the Business Sponsor form visible - in the top right there should be an edit button which should be greyed out 
- The Credit Questionnaire section should have now have all of the fields from the Credit Questionnaire form visible - in the top right there should be an edit button which should be greyed out 
- At this stage the Legal Review section should have now have all of the fields from the Legal Review form visible - in the top right there should be an edit button which should be greyed out 
- The Credit Analysis section should have now have all of the fields from the Credit Analysis form visible - in the top right there should be an edit button which should be greyed out 
- The Documents Upload section should show any documents uploaded so far
- The Documents section should be its own section rather than the documents button previously seen in the actions section
- The Approval section should now be visible on the bottom showing the current status  - there should be an edit button which should allow the approver to take it into edit mode and edit the Approval form

Once approved or rejected the workflow is complete.

Once you have reviewed please feel free to ask any questions which require clarification before you propose a detailed plan.