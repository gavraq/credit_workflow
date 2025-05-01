# Credit Workflow Application - Forms, Views, and Templates

## Overview

This document provides a comprehensive overview of the Credit Workflow application's core components: forms, views, and templates. It consolidates information about each major functionality area and describes how they interact to create a cohesive credit risk management system.

The Credit Workflow application follows a consistent design pattern across its components, with each section serving a specific purpose in the credit request lifecycle:

1. **Credit Request Form**: Initial submission of credit requests (multi-step wizard)
2. **Credit Review Form**: Credit risk assessment and analysis
3. **Credit Questionnaire Form**: Detailed counterparty information gathering
4. **Legal Review Form**: Legal risk assessment and documentation
5. **Credit Analysis Form**: Comprehensive financial and risk analysis

## Application Architecture

### Common Design Patterns

The application employs several consistent design patterns across all its forms and templates:

1. **Model-View-Template Architecture**
   - Clear separation of data models, view logic, and presentation templates
   - Consistent naming conventions for models, views, forms, and templates

2. **Base Form Class**
   - `BaseForm` class that extends Django's ModelForm
   - Provides common styling, error handling, and validation helpers
   - Used as the foundation for all application forms

3. **Bootstrap 5 Frontend**
   - Consistent use of Bootstrap 5 components and styling
   - Card-based layouts with shadow effects for visual hierarchy
   - Responsive grid system for layout flexibility

4. **Consistent Navigation**
   - Sidebar navigation with standard sections and icons
   - Active state highlighting for current section
   - Hierarchical organization of navigation items

5. **Draft Support**
   - Most forms support draft state for works in progress
   - Clear indication of draft vs. submitted status
   - Consistent handling of draft state in views and templates

6. **Workflow Integration**
   - Forms connect to a workflow state system
   - Actions can transition requests between states
   - UI adapts based on current workflow state

### Data Models

The application is built around several key data models:

1. **CreditRequest**
   - Central model representing a credit request
   - Contains core request information, status, and relationships
   - Referenced by most other models in the system

2. **CreditLimit**
   - Represents credit limits associated with a request
   - Many-to-one relationship with CreditRequest
   - Contains existing and proposed limit information

3. **CreditQuestionnaire**
   - Stores detailed questionnaire responses
   - One-to-one relationship with CreditRequest
   - Uses structured markdown for content storage

4. **LegalReview**
   - Contains legal risk assessment information
   - One-to-one relationship with CreditRequest
   - Supports draft and final submission states

5. **CreditAnalysis**
   - Comprehensive financial and risk analysis
   - One-to-one relationship with CreditRequest
   - Uses structured markdown for content storage

6. **WorkflowState**
   - Represents different states in the credit approval process
   - Referenced by CreditRequest to track current status
   - Used for controlling access and transitions

## Form Implementations

### 1. Credit Request Form

The Credit Request form is implemented as a multi-step wizard that guides users through the process of creating a new credit request.

#### Key Features

- **Multi-Step Wizard**: Breaks down the complex credit request process into four logical steps
- **Dynamic Limit Management**: Allows adding and removing credit limits dynamically
- **Role-Based Field Filtering**: Shows only appropriate users in business sponsor selection
- **Conditional Form Elements**: Displays or hides fields based on user selections
- **Workflow Integration**: Sets initial workflow state based on submission type

#### Implementation Details

- Uses Django's `SessionWizardView` for managing the multi-step process
- Implements four form classes for different steps:
  - `CreditRequestStep1Form`: Basic information (counterparty, title, priority)
  - `CreditLimitBaseFormSet`: Dynamic management of credit limits
  - `CreditRequestStep3Form`: Relationship information and financials
  - `CreditRequestStep4Form`: Business justification and sponsorship
- Custom JavaScript for dynamic limit management in step 2
- Dedicated template for each step with consistent styling

#### URL Patterns

```python
path('credit-request/wizard/', CreditRequestWizard.as_view(), name='creditrequest_wizard'),
path('credit-request/new/', views.CreditRequestCreateView.as_view(), name='creditrequest_create'),
path('credit-request/<int:pk>/edit/', views.CreditRequestUpdateView.as_view(), name='creditrequest_update'),
```

### 2. Credit Review Form

The Credit Review form allows authorized reviewers to assess credit requests and document their findings.

#### Key Features

- **Workflow State Control**: Only accessible for requests in the "CREDIT_REVIEW" state
- **Comprehensive Request Summary**: Displays all relevant request details for review
- **Workflow Transition**: Automatically advances the workflow state upon submission
- **Analyst Assignment**: Allows selection of an appropriate credit analyst

#### Implementation Details

- Uses Django's `UpdateView` operating on the CreditRequest model
- Implements access control based on workflow state
- `CreditReviewForm` focuses on review-specific fields:
  - assigned_analyst
  - questionnaire_required
  - da_level
  - credit_review_notes
- Template includes detailed display of the credit request being reviewed

#### URL Pattern

```python
path('credit-request/<int:pk>/review/', views.CreditReviewUpdateView.as_view(), name='creditrequest_review'),
```

### 3. Credit Questionnaire Form

The Credit Questionnaire form collects detailed information about a counterparty's business model, trading activities, and financial structure.

#### Key Features

- **Structured Sections**: Organizes questions into logical sections by topic
- **Markdown Formatting**: Compiles responses into a structured markdown document
- **Draft Support**: Allows saving partial progress as drafts
- **Pre-filling**: Can pre-fill the credit request from URL parameters

#### Implementation Details

- Uses standard Django `CreateView` and `UpdateView` classes
- `CreditQuestionnaireForm` with a hidden content field
- Custom JavaScript that compiles multiple input fields into a structured markdown document
- Multiple card sections in the template for different questionnaire topics

#### URL Patterns

```python
path('questionnaire/new/', views.CreditQuestionnaireCreateView.as_view(), name='creditquestionnaire_create'),
path('questionnaire/<int:pk>/edit/', views.CreditQuestionnaireUpdateView.as_view(), name='creditquestionnaire_update'),
```

### 4. Legal Review Form

The Legal Review form enables legal professionals to document legal considerations and risks associated with credit requests.

#### Key Features

- **Simple Interface**: Focused on capturing detailed legal analysis
- **Draft Support**: Allows saving partial progress as drafts
- **Reviewer Assignment**: Automatically sets the current user as the reviewer

#### Implementation Details

- Uses standard Django `CreateView` and `UpdateView` classes
- `LegalReviewForm` with a focus on the comments field
- Simple template with a card for the legal review details

#### URL Patterns

```python
path('legalreview/new/', views.LegalReviewCreateView.as_view(), name='legalreview_create'),
path('legalreview/<int:pk>/edit/', views.LegalReviewUpdateView.as_view(), name='legalreview_update'),
```

### 5. Credit Analysis Form

The Credit Analysis form provides a comprehensive interface for analyzing financial information and credit risk.

#### Key Features

- **Multi-Tab Interface**: Organizes the analysis into logical sections
- **Financial Tables**: Structured display of financial data
- **Markdown Formatting**: Compiles section content into a structured document
- **Draft Support**: Allows saving partial progress as drafts

#### Implementation Details

- Uses standard Django `CreateView` and `UpdateView` classes
- `CreditAnalysisForm` with multiple section fields
- Custom method to compile sections into a structured markdown document
- Tab-based navigation in the template

#### URL Patterns

```python
path('creditanalysis/new/', views.CreditAnalysisCreateView.as_view(), name='creditanalysis_create'),
path('creditanalysis/<int:pk>/edit/', views.CreditAnalysisUpdateView.as_view(), name='creditanalysis_update'),
path('creditanalysis/<int:pk>/', views.CreditAnalysisDetailView.as_view(), name='creditanalysis_detail'),
```

## Template Design Patterns

### Common Structure

All templates in the application follow a consistent structure:

1. **Base Template Extension**
   ```html
   {% extends 'base.html' %}
   {% load widget_tweaks %}
   ```

2. **Sidebar Navigation**
   ```html
   {% block sidebar %}
   <nav class="sidebar text-white" style="width: 220px; background-color: #174EA6; min-height: 100vh; padding: 0;">
     <!-- Navigation items -->
   </nav>
   {% endblock %}
   ```

3. **Main Content Container**
   ```html
   {% block content %}
   <div class="container mt-5 pt-3">
     <!-- Page title and content -->
   </div>
   {% endblock %}
   ```

4. **Card-Based Layout**
   ```html
   <div class="card shadow-sm mb-4">
     <div class="card-body">
       <h5 class="card-title mb-4">Section Title</h5>
       <!-- Form fields or content -->
     </div>
   </div>
   ```

5. **Form Controls**
   ```html
   <div class="d-flex justify-content-end">
     <button type="submit" name="save_draft" class="btn btn-secondary me-2">Save as Draft</button>
     <button type="submit" class="btn btn-primary">Submit</button>
   </div>
   ```

### Form Field Styling

Form fields use consistent styling through the Django widget_tweaks library:

```html
<div class="col-12 mb-3">
  <label for="{{ form.field.id_for_label }}" class="form-label">Field Label</label>
  {{ form.field|add_class:'form-control' }}
  {% if form.field.errors %}
    <div class="invalid-feedback d-block">{{ form.field.errors }}</div>
  {% endif %}
  <small class="text-muted">Helper text for the field</small>
</div>
```

### Responsive Design

All templates use Bootstrap's responsive grid system:

```html
<div class="row g-3">
  <div class="col-md-6 mb-3">
    <!-- Half-width on medium+ screens, full width on small screens -->
  </div>
  <div class="col-md-6 mb-3">
    <!-- Half-width on medium+ screens, full width on small screens -->
  </div>
</div>
```

## View Design Patterns

### Common Base Classes

Most views in the application extend Django's generic class-based views with authentication requirements:

```python
class SomeCreateView(LoginRequiredMixin, CreateView):
    model = SomeModel
    form_class = SomeForm
    template_name = 'credit_workflow/some_form.html'
```

### Form Handling Patterns

Views consistently handle form submission and user attribution:

```python
def form_valid(self, form):
    # Set the user
    form.instance.author = self.request.user
    
    # Handle draft state
    form.instance.is_draft = 'save_draft' in self.request.POST
    
    return super().form_valid(form)
```

### Success Messages

Many views provide user feedback via Django's messages framework:

```python
def get_success_url(self):
    if self.object.is_draft:
        messages.success(self.request, 'Item saved as draft.')
    else:
        messages.success(self.request, 'Item submitted successfully.')
    return reverse_lazy('some_detail', kwargs={'pk': self.object.pk})
```

### Context Enhancement

Views often add additional context for templates:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['additional_data'] = SomeModel.objects.filter(some_condition)
    return context
```

## Integration Between Components

The application components work together to create a cohesive workflow:

1. **Credit Request Creation**
   - User creates a credit request through the multi-step wizard
   - Request enters the workflow in the initial state

2. **Credit Review**
   - Authorized reviewers assess requests in the "CREDIT_REVIEW" state
   - Review can determine if a questionnaire is required
   - Completing the review advances the workflow state

3. **Credit Questionnaire**
   - If required, a questionnaire is completed for the credit request
   - Questionnaire provides detailed information for analysis

4. **Legal Review**
   - Legal team can review the credit request
   - Legal review documents legal considerations and risks

5. **Credit Analysis**
   - Credit analysts perform comprehensive financial analysis
   - Analysis documents findings and recommendations

6. **Credit Request Detail**
   - Central hub showing the status of all components
   - Provides navigation to view or create related components
   - Shows workflow progression

## URL Structure

The application uses a logical URL structure for its components:

- `/` - Dashboard (home page)
- `/credit-request/` - Credit request listing
- `/credit-request/wizard/` - Multi-step credit request wizard
- `/credit-request/new/` - Single-page credit request form
- `/credit-request/<id>/` - Credit request detail
- `/credit-request/<id>/edit/` - Edit credit request
- `/credit-request/<id>/review/` - Credit review form
- `/questionnaire/new/` - Create questionnaire
- `/questionnaire/<id>/edit/` - Edit questionnaire
- `/legalreview/new/` - Create legal review
- `/legalreview/<id>/edit/` - Edit legal review
- `/creditanalysis/new/` - Create credit analysis
- `/creditanalysis/<id>/` - View credit analysis
- `/creditanalysis/<id>/edit/` - Edit credit analysis
- `/documents/upload/` - Upload documents
- `/documents/<credit_request_id>/` - View documents for a credit request
- `/notifications/` - Notification center
- `/notification-preferences/` - Notification preferences

## Common JavaScript Patterns

Several forms use JavaScript for enhancing functionality:

### Form Compilation

The questionnaire and analysis forms compile multiple fields into a structured format:

```javascript
// Compile multiple fields into structured content
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Build content from multiple fields
        let content = '';
        sections.forEach(section => {
            content += `## ${section.title}\n\n`;
            // Add section content
        });
        
        // Set the compiled content
        document.querySelector('[name="content"]').value = content;
        
        // Submit the form
        form.submit();
    });
});
```

### Dynamic Form Elements

The credit request wizard uses JavaScript for dynamic limit management:

```javascript
// Add new limit row
function addLimit() {
    // Create new limit entry
    const limitEntry = {
        limit_type: document.querySelector('#id_limit_type').value,
        // Get other field values
    };
    
    // Add to list and update display
    limitRequests.push(limitEntry);
    updateLimitTable();
}
```

## Future Development Areas

The application has several areas for potential expansion:

1. **Workflow Customization**
   - Configurable workflow states and transitions
   - Role-based workflow permissions

2. **Reporting and Analytics**
   - Dashboards for request status and metrics
   - Export functionality for reports

3. **Enhanced Collaboration**
   - Comments and discussion on credit requests
   - Multi-user editing for questionnaires and analyses

4. **Integration Capabilities**
   - API endpoints for external system integration
   - Batch import/export functionality

5. **Advanced Document Management**
   - Document version control
   - Document templates and generation

## Conclusion

The Credit Workflow application implements a comprehensive set of forms, views, and templates to support the credit request and approval process. The consistent design patterns across components create a cohesive user experience, while the modular architecture allows for future expansion and customization.

The application demonstrates effective use of Django's form handling, class-based views, and template system, combined with modern frontend techniques using Bootstrap and JavaScript. The workflow-based approach provides a structured process for managing credit requests through their lifecycle, from initial submission to final approval.