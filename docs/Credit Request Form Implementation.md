# Credit Request Form Implementation

## Overview

This document describes the implementation of the multi-step credit request form for the Credit Workflow application. The form is implemented as a wizard with four steps:

1. Basic Information
2. Limit Requests
3. Relationship Information
4. Business Justification

The form guides users through the process of creating a new credit request, collecting all necessary information in a logical, step-by-step manner.

## Technology Stack

- **Backend**: Django 5.2
- **Frontend**: Bootstrap 5, JavaScript
- **Database**: PostgreSQL
- **Form Processing**: Django formtools (for the SessionWizardView)

## Data Model

The primary models involved in the credit request form are:

- `CreditRequest`: The main model that stores the credit request data
- `CreditLimit`: A related model for storing limit information (many-to-one relationship with CreditRequest)
- `LimitType`: A model for categorizing different types of credit limits
- `CounterParty`: A model representing the entities for which credit requests are submitted
- `User`: Django's user model, extended to include roles such as business sponsor

## Form Implementation

### Wizard Structure

The form is implemented using Django's `SessionWizardView` to manage the multi-step process. The main components are:

```python
# Define the form list for the wizard
FORMS = [
    ("step1", CreditRequestStep1Form),
    ("step2", CreditLimitBaseFormSet),
    ("step3", CreditRequestStep3Form),
    ("step4", CreditRequestStep4Form),
]

# Define templates for each step
TEMPLATES = {
    "step1": "credit_workflow/credit_request_step1.html",
    "step2": "credit_workflow/credit_request_step2.html",
    "step3": "credit_workflow/credit_request_step3.html",
    "step4": "credit_workflow/credit_request_step4.html",
}
```

### Step 1: Basic Information

**Form Fields:**
- Counterparty (foreign key)
- Title (text)
- Priority (radio select: Low, Medium, High)
- Required By Date (date)

**UI Components:**
- Dropdown for counterparty selection
- Text input for title
- Radio buttons for priority
- Date picker for required by date

### Step 2: Limit Requests

Step 2 allows users to dynamically add multiple limit requests to the credit request.

**Form Fields for Each Limit:**
- Limit Type (foreign key to LimitType)
- Existing Amount (decimal)
- Existing Tenor (integer, months)
- Proposed Amount (decimal)
- Proposed Tenor (integer, months)

**UI Components:**
- Dynamic table for displaying added limits
- Form for adding new limits with:
  - Dropdown for limit type
  - Number inputs for amounts and tenors
  - Add button to submit new limit
  - Remove buttons to delete existing limits

**JavaScript Functionality:**
- Dynamic addition of new limit rows
- Removal of existing limit rows
- JSON storage of limit data
- Form validation before submission

### Step 3: Relationship Information

**Form Fields:**
- Client Introduction Details (text area)
- KYC Approval Status (toggle: Approved/Not Approved)
- Senior Client Contact (text)
- Last Client Visit Date (date)
- Financial Information:
  - Revenue Last 12 Months (decimal)
  - Projected Revenue (decimal)
  - Projected RoRWA Percentage (decimal)
- Financial Disclosure:
  - Financial Statements Received (boolean toggle)
  - Interim Financials Info (text area, conditional)

**UI Components:**
- Text area for client introduction
- Toggle switches for approval statuses
- Text input for senior client contact
- Date picker for last visit date
- Number inputs with currency/percentage symbols for financial data
- Toggle switches for financial disclosure questions

**JavaScript Functionality:**
- Show/hide interim financials information based on toggle state

### Step 4: Business Justification

**Form Fields:**
- Description (text area)
- Country Risk Limit Confirmed (boolean)
- Business Sponsor (foreign key to User with business_sponsor role)

**UI Components:**
- Text area for detailed business justification
- Toggle switch for country risk limit confirmation
- Dropdown showing only users with business sponsor role, displaying their full names

## UI Design and Consistency

The UI follows a consistent design pattern across all steps:

1. **Header Section**
   - Step title and number
   - Progress bar showing completion percentage

2. **Main Content Card**
   - Card with shadow for visual depth
   - Section headings and sub-headings
   - Consistent form controls with labels and helper text
   - Validation error display

3. **Footer Section**
   - Previous/Next navigation buttons
   - Clear call-to-action styling

## Form Processing and Data Handling

1. **Data Storage During Wizard Process**
   - Form data is stored in the session between steps
   - Limit data is stored as JSON to handle the dynamic nature of the form

2. **Final Submission Process**
   - Create the CreditRequest object with fields from steps 1, 3, and 4
   - Create CreditLimit objects for each limit request from step 2
   - Set required relationships (workflow state, submitter)
   - Handle business sponsor assignment

## Special Features

1. **Dynamic Limit Request Management**
   - Add multiple limit requests without page reload
   - Validate each limit request before adding to the table
   - Store all limit requests in a hidden JSON field

2. **Role-Based Field Filtering**
   - Business sponsor dropdown shows only users with the business_sponsor role
   - Names displayed as "First Last" instead of usernames

3. **Conditional Form Elements**
   - Interim financials section appears only when the toggle is switched on
   - Data is preserved when navigating back to previous steps

4. **Mobile-Responsive Design**
   - All form elements adapt to different screen sizes
   - Column layouts adjust for smaller screens

## Implementation Challenges and Solutions

1. **Challenge**: Migration of the `limit_type` field from CharField to ForeignKey
   **Solution**: Created a multi-step migration process that:
   - Created the LimitType model
   - Populated it with predefined limit types
   - Added a temporary field to store original values
   - Converted the data to use foreign keys
   - Removed the temporary field

2. **Challenge**: Dynamic form handling for limit requests
   **Solution**: Used a combination of:
   - FormSets for server-side processing
   - JavaScript for client-side dynamic updates
   - JSON storage for passing complex data between steps

3. **Challenge**: Consistent styling across all steps
   **Solution**: 
   - Implemented a consistent Bootstrap-based design system
   - Created reusable form layouts and components
   - Applied the same visual patterns across all steps

## Future Enhancements

1. **Form Validation Improvements**
   - Add more client-side validation
   - Implement cross-field validation rules

2. **User Experience Enhancements**
   - Add auto-save functionality
   - Implement a draft system for partial submissions

3. **Integration Features**
   - Connect with document upload system
   - Integrate with notification system for status updates

## Conclusion

The multi-step credit request form provides a streamlined, user-friendly interface for submitting complex credit requests. The wizard format breaks down the process into logical steps, guiding users through the required information while maintaining a consistent, responsive design throughout.

The implementation balances the need for collecting comprehensive information with providing a good user experience, leveraging Django's form handling capabilities alongside modern frontend techniques to create a robust, maintainable solution.
