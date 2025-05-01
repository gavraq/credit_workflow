# Automated API Documentation (Swagger UI & Redoc)

## What is Automated API Documentation?
Automated API documentation tools like **Swagger UI** and **Redoc** provide a live, interactive web interface for your API, generated directly from your OpenAPI schema and Django REST Framework (DRF) code. They allow you and your team to:

- Browse all available API endpoints, methods, and parameters.
- See request/response schemas, authentication requirements, and example payloads.
- Try out API requests directly from the browser (with authentication).
- Always stay up-to-date as your API evolves—no manual syncing required.

## How is This Set Up?
- We use the [`drf-yasg`](https://drf-yasg.readthedocs.io/en/stable/) package for Django REST Framework.
- Swagger UI is available at `/swagger/` (e.g., http://localhost:8001/swagger/).
- Redoc is available at `/redoc/` (e.g., http://localhost:8001/redoc/).
- These endpoints are always in sync with your code and serializers, so your documentation is always current.

## Why is This Best Practice?
- **Developer Experience:** Makes onboarding and API exploration easy for developers and integrators.
- **Accuracy:** Docs update automatically as your API changes.
- **Interactivity:** Enables real-time testing and exploration of endpoints.
- **Professionalism:** Provides a polished, modern API reference for internal and external users.

---

## Usage Examples

### Authentication
All endpoints require authentication (JWT or session). Example header:
```
Authorization: Bearer <your-token>
```

### Example: List Credit Requests
```
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/credit-requests/
```

### Example: Transition a CreditRequest
```
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"to_state_id": 2, "action_name": "approve"}' \
  http://localhost:8001/api/credit-requests/1/transition/
```

### Using OpenAPI YAML in Postman
- Import `docs/openapi.yaml` into Postman for automatic endpoint and schema discovery.

---

## Technical Setup
- `drf-yasg` is installed and added to `INSTALLED_APPS`.
- Swagger UI and Redoc endpoints are registered in `django_project/urls.py`.
- No manual syncing needed—just maintain your DRF code and serializers.

---

For more, see [drf-yasg documentation](https://drf-yasg.readthedocs.io/en/stable/).
