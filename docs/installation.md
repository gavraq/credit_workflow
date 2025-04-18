# Installation Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- uv (for Python environment management)
- Git

## Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/credit_workflow.git
   cd credit_workflow
   ```

2. **Set up the uv virtual environment and install dependencies**
   ```bash
   uv venv .venv
   uv pip install -r requirements.txt  # Only if requirements.txt exists and you are migrating from pip
   # Otherwise, use:
   uv pip install django psycopg python-dotenv  # Or use 'uv add <package>' for new dependencies
   ```
   > **Note:** For new projects, use `uv add <package>` to manage dependencies (e.g., `uv add django psycopg python-dotenv`).
   > If migrating from an existing pip-based project, you may use `uv pip install -r requirements.txt` once, then switch to uv's workflow.

3. **Configure environment variables**
   - Copy `.env.example` to `.env` and edit as needed.

4. **Database setup**
   - Ensure PostgreSQL is running.
   - Create the database and user as per `.env`.

5. **Run migrations**
   ```bash
   uv run python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   uv run python manage.py runserver
   ```

Visit [http://localhost:8000](http://localhost:8000) to verify the setup.
