# Deployment Guide

## Environments
| Environment | DB         | Static/Media | Debug | Secrets         | Notes                   |
|-------------|------------|--------------|-------|-----------------|-------------------------|
| Dev         | SQLite/PG  | Local        | Yes   | .env (local)    | For local development   |
| Staging     | PostgreSQL | S3/WhiteNoise| No    | .env (secure)   | Mirrors production      |
| Production  | PostgreSQL | S3/WhiteNoise| No    | .env (secure)   | Hardened, monitored     |

## Environment Setup
1. **Clone repo**
2. **Set up `.env`** (see example below)
3. **Install dependencies**
   ```bash
   uv venv .venv
   uv add django psycopg2-binary python-dotenv whitenoise gunicorn drf-yasg
   # Add celery[redis] if using background tasks
   ```
4. **Run migrations**
   ```bash
   uv run python manage.py migrate
   ```
5. **Collect static files**
   ```bash
   uv run python manage.py collectstatic
   ```
6. **Create superuser**
   ```bash
   uv run python manage.py createsuperuser
   ```
7. **Start server**
   - Dev: `uv run python manage.py runserver`
   - Prod: `gunicorn django_project.wsgi:application --bind 0.0.0.0:8000`

## Static & Media Files
- **Dev:** Served by Django.
- **Prod:** Use [WhiteNoise](https://whitenoise.evans.io/) or S3 for static/media files. Update `STATIC_ROOT`, `MEDIA_ROOT`, and storage backends in `settings.py`.

## Secure Production Server
- Use `gunicorn` or `uwsgi` behind `nginx`.
- Configure `nginx` for SSL (Let's Encrypt recommended).
- Set `DEBUG=False`, proper `ALLOWED_HOSTS`, and secure proxy headers.

## Health Checks & Monitoring
- Use `/admin/` for manual checks.
- Integrate with uptime monitoring (Pingdom, UptimeRobot).
- Log errors to file or external service (Sentry, etc).

## Rollback & Disaster Recovery
- Take regular PostgreSQL backups (e.g., `pg_dump`).
- Store backups securely (offsite/S3).
- Document and test restore procedures.

## Celery/Redis/PDF Notes
- If using Celery: run worker with `uv run celery -A django_project worker -l info` and Redis as broker.
- For PDF (WeasyPrint): ensure system dependencies are installed (see WeasyPrint docs).

## Example .env
```
DEBUG=False
SECRET_KEY=your-secret
DATABASE_URL=postgres://user:pass@host:5432/dbname
ALLOWED_HOSTS=yourdomain.com
STATIC_ROOT=/app/static
MEDIA_ROOT=/app/media
EMAIL_HOST=smtp.yourprovider.com
```

## Troubleshooting
- Use Django Debug Toolbar in dev.
- Check logs: `logs/`, `systemctl status`, `journalctl` (for gunicorn/nginx).
- Common issues: missing migrations, static files, misconfigured env vars.
