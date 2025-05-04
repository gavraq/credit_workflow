# Credit Risk Workflow Application

## Overview

This Django application implements a comprehensive credit risk workflow system that allows financial organizations to manage their credit request lifecycle. The system supports multiple roles (Relationship Managers, Credit Analysts, Business Sponsors, Legal Reviewers) and includes a state machine workflow to track the progression of credit requests through various stages.

## Recent Enhancements

The application has been enhanced with the following improvements:

1. **Enhanced Credit Request Detail View**
   - Added comprehensive view of all components of a credit request
   - Implemented workflow progress visualization
   - Added permission checks for each section based on user role and workflow state

2. **Improved Component Structure**
   - Created separate template components for each section of a credit request
   - Implemented better UI for displaying credit request information, reviews, and analyses
   - Added document management capabilities

3. **Role-Based Task Assignment**
   - Added "Assigned Requests" view to show tasks based on user role
   - Improved filtering and sorting of credit requests
   - Enhanced dashboard with role-specific quick links

4. **UI/UX Improvements**
   - Implemented responsive design using Bootstrap 5
   - Added workflow progress visualization
   - Enhanced navigation and dashboard
   - Added notification center and preferences

## Key Components

The application includes several key components:

1. **Views**
   - `CreditRequestDetailView`: Displays all components of a credit request
   - `AssignedRequestsView`: Shows tasks assigned to the current user
   - `CreditRequestListView`: Lists all credit requests with filtering
   - Various component-specific views (CreditReview, BusinessSponsorship, etc.)

2. **Templates**
   - Base layout templates with navigation and common elements
   - Component templates for modular display of credit request sections
   - Role-specific views for different user types

3. **State Machine**
   - Workflow states tracking the progression of credit requests
   - Permission checks based on workflow state
   - Timestamp tracking for workflow transitions

4. **Notifications**
   - Notification system for workflow changes and assignments
   - Customizable notification preferences
   - Email and in-app notification channels

## Directory Structure

```
credit_workflow/
├── models.py                  # Data models (CreditRequest, Questionnaire, etc.)
├── views.py                   # View classes for rendering templates
├── views_detailview.py        # Enhanced CreditRequestDetailView implementation
├── views_wizard.py            # Credit request creation wizard
├── views_sponsorship.py       # Business sponsorship views
├── urls.py                    # URL routing for the application
├── forms.py                   # Form classes for data input
├── templates/
│   └── credit_workflow/
│       ├── base.html          # Base template with layout
│       ├── components/        # Reusable template components
│       │   ├── navigation.html
│       │   ├── workflow_progress.html
│       │   ├── credit_request_info.html
│       │   └── ...
│       ├── creditrequest_detail.html
│       ├── creditrequest_list.html
│       ├── assigned_requests.html
│       ├── dashboard.html
│       └── ...
├── static/
│   └── credit_workflow/
│       ├── css/
│       │   ├── styles.css     # Main styles
│       │   └── workflow_progress.css
│       └── js/
│           └── main.js        # Client-side functionality
└── templatetags/
    ├── __init__.py
    └── credit_workflow_extras.py  # Custom template filters
```

## Usage

1. **Dashboard**
   - Start at the dashboard to see an overview of your credit requests
   - Use quick links to navigate to different sections

2. **Credit Requests**
   - View all credit requests or use filters to find specific ones
   - Create new credit requests with the wizard
   - Use the detail view to see all components of a credit request

3. **My Tasks**
   - View requests assigned to you based on your role
   - Take action on assigned tasks directly from the task list

4. **Workflow Progression**
   - Follow the workflow progress bar to track request status
   - Submit credit requests for review
   - Approve or request changes as requests move through workflow stages

## Future Enhancements

Planned enhancements for the application include:

1. API endpoints for integration with other systems
2. Advanced reporting and analytics
3. Improved document management with versioning
4. Enhanced commenting and collaboration features
5. Audit trail and compliance reporting