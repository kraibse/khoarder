# Testing

## Backend

Install test dependencies:
```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
```

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_topics.py -v
```

Tests use an in-memory SQLite database and mock PostgreSQL FTS functions for compatibility.

## Frontend

Install dependencies (if not already):
```bash
cd frontend
pnpm install
```

Run tests:
```bash
pnpm run test
```

Run tests in watch mode:
```bash
pnpm run test:watch
```

Type check without emitting:
```bash
pnpm run type-check
```
