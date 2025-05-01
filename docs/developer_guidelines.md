# Developer Guidelines

## Code Style & Conventions
- Follow [PEP 8](https://pep8.org/) for Python code.
- Use Django’s conventions for apps, models, views, and templates.
- Naming: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants.
- Keep files <300 lines when possible; refactor if larger.

## Onboarding & Local Setup
1. Fork and clone the repo.
2. Set up `.env` (see example in deployment docs).
3. Install dependencies with `uv venv .venv` and `uv add <package>`.
4. Run migrations and start the server locally.

## Branching, Commits, and PRs
- Use feature branches: `feature/<short-description>`.
- Write clear, descriptive commit messages.
- Open PRs against `main` with detailed descriptions.
- Reference related issues in PRs.

## Code Review Process
- All code changes require peer review before merging.
- Use PR review tools (GitHub/GitLab).
- Address all requested changes before merge.
- Review for code clarity, test coverage, and adherence to standards.

## Security & Secrets Management
- Never commit secrets or credentials.
- Use `.env` for all sensitive config.
- Do not overwrite `.env` without confirmation.
- Use Django security best practices (CSRF, XSS, SQL injection protection).

## Extensibility
- Add workflow steps, document types, or API endpoints by:
  - Creating new models/serializers/views as needed.
  - Registering admin and API routes.
  - Keeping business logic in service layers.
- Avoid code duplication; reuse existing patterns.

## Testing & Coverage
- Write tests for all major features (models, services, APIs).
- Use Django’s test runner or pytest-django.
- Strive for high coverage, especially on business logic.
- Run tests:
  ```bash
  uv run python manage.py test
  ```

## Issue Reporting
- Use issue tracker for bugs, enhancements, and questions.
- Provide clear steps to reproduce, expected/actual results, and environment info.

## Useful Commands
| Task                  | Command                                      |
|-----------------------|----------------------------------------------|
| Run server            | uv run python manage.py runserver            |
| Run tests             | uv run python manage.py test                 |
| Make migrations       | uv run python manage.py makemigrations       |
| Migrate DB            | uv run python manage.py migrate              |
| Create superuser      | uv run python manage.py createsuperuser      |
| Collect static files  | uv run python manage.py collectstatic        |
| Install dependency    | uv add <package>                             |

## Contribution Guidelines
- Fork and branch from `main`.
- Use feature branches: `feature/<short-description>`.
- Open pull requests with clear descriptions.

## Code Review Process
- All code changes are peer-reviewed.
- Use GitHub/GitLab PR review tools.
- Address requested changes before merging.

## Extensibility
- Add new workflow steps or document types by creating new models and registering them in admin and API.
- Use service layers for business logic (not in views/models).

## Testing Strategy
- Write tests for all major features (models, services, API endpoints).
- Use Django’s test runner or pytest-django.
- Run tests with:
  ```bash
  uv run python manage.py test
  ```

## Branching & Commit Messages

- Use feature branches: `feature/<short-description>`
- Write clear, descriptive commit messages.

## Adding Dependencies

- Use `uv add <package>` to add dependencies.
- Never commit secrets or credentials.

## Testing

- Write tests for all major features.
- Run tests with:
  ```bash
  uv run python manage.py test
  ```

## Environment Management

- Use `.env` for local settings.
- Never commit `.env` to version control.

## Useful Commands

- Run server: `uv run python manage.py runserver`
- Run tests: `uv run python manage.py test`
- Make migrations: `uv run python manage.py makemigrations`
