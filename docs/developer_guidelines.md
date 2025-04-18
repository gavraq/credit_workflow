# Developer Guidelines

## Code Style

- Follow [PEP 8](https://pep8.org/) for Python code.
- Use Django’s conventions for apps, models, views, and templates.

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
