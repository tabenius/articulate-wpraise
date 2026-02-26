# MCP Server Tests

Integration tests for critical security paths:
- User authentication and session management
- Connection management and password encryption
- URL validation and SSRF protection
- Authorization checks

## Running Tests

```bash
# Run all tests
docker exec articulate-mcp pytest /app/tests/ -v

# Run specific test file
docker exec articulate-mcp pytest /app/tests/test_user_manager.py -v

# Run with coverage
docker exec articulate-mcp pytest /app/tests/ --cov=articulate_mcp --cov-report=html
```

## Test Database

Tests use the same database as the application but with cleanup after each test.
Ensure the database is running before running tests.

## Coverage Goals

- UserManager: Authentication, session management, password hashing
- ConnectionManager: CRUD operations, encryption/decryption, URL validation
- Auth endpoints: Register, login, logout, /me
- Authorization: MCP tool access control
