# Credit Risk Workflow Application

A Django application for managing credit risk workflows.

## Project Structure

This application follows a Django project structure with the following main components:

- `credit_workflow`: Main application for credit request management
- `workflow`: State machine implementation for workflow management
- `users`: User management application
- `notifications`: Notification system for workflow events
- `documents`: Document management for credit requests

## Installation

1. Clone the repository
2. Create a virtual environment
3. Install dependencies with `pip install -r requirements.txt`
4. Run migrations with `python manage.py migrate`
5. Create a superuser with `python manage.py createsuperuser`
6. Start the development server with `python manage.py runserver`

## Workflow Stages

1. Credit Request Submission
2. Credit Review
3. Business Sponsorship
4. Parallel Processing:
   - Credit Questionnaire
   - Legal Review
   - Credit Analysis
5. Credit Paper Compilation
6. Final Approval

## License

This project is private and proprietary.