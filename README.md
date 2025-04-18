# Credit Risk Workflow System

A Django-based web application for managing and analyzing credit risk workflows.

## Features

- User authentication and role-based access
- Credit application submission and review
- Automated risk scoring
- Document upload and management
- Audit trails and reporting

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/credit_workflow.git
cd credit_workflow

# Set up virtual environment and install dependencies
uv venv .venv
uv pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and secret settings

# Apply migrations and start the server
uv run python manage.py migrate
uv run python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000) to get started.

## Documentation

- [Installation Guide](docs/installation.md)
- [Developer Guidelines](docs/developer_guidelines.md)
- [System Architecture Overview](docs/architecture.md)
- [API Reference](docs/api/)
- [Setup Guides](docs/setup/)

## License

MIT License. See [LICENSE](LICENSE).
