# Articulate MCP Server Test Suite

Comprehensive pytest-based test suite for all MCP server endpoints.

## Installation

```bash
cd tests
pip install -r requirements.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test class
```bash
pytest test_mcp_server.py::TestAuthentication
pytest test_mcp_server.py::TestProfile
pytest test_mcp_server.py::TestOrganizations
pytest test_mcp_server.py::TestInvites
```

### Run with markers
```bash
pytest -m auth
pytest -m organizations
```

### Run in parallel (faster)
```bash
pytest -n auto
```

### Run with verbose output
```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run specific test
```bash
pytest test_mcp_server.py::TestAuthentication::test_login
```

## Test Coverage

### Endpoints Tested

**Health:**
- ✅ GET /health
- ✅ GET /health/ready

**Authentication:**
- ✅ POST /register
- ✅ POST /login
- ✅ GET /me
- ✅ POST /logout (via cleanup)

**Profile:**
- ✅ GET /profile
- ✅ PUT /profile
- ✅ GET /profile/{username}
- ✅ DELETE /profile (via cleanup)

**Organizations:**
- ✅ POST /organizations (create)
- ✅ GET /organizations (list)
- ✅ GET /organizations/{id}
- ✅ PUT /organizations/{id}
- ✅ GET /organizations/{id}/members
- ✅ DELETE /organizations/{id} (via cleanup)

**Invites:**
- ✅ POST /organizations/{id}/invites (create)
- ✅ GET /invites (user's invites)
- ✅ POST /invites/accept
- ✅ POST /invites/reject (TODO)

**File Upload:**
- TODO: POST /upload

**WordPress Connections:**
- TODO: Connection CRUD operations

## Test Structure

### Fixtures

- `base_url`: API base URL
- `test_user_credentials`: Test user credentials
- `registered_user`: Registered test user (session scope)
- `auth_session`: Authenticated session with headers (session scope)
- `second_user`: Second test user for multi-user tests (function scope)

### Resource Tracking

Tests track created resources (organizations, connections, invites) and clean them up automatically at the end of the test run.

### Defensive Programming

- All tests include proper assertions
- Timeout protection (30s default)
- Automatic cleanup of test data
- Session-scoped fixtures for efficiency
- Resource tracking prevents data pollution

## Configuration

Edit `pytest.ini` to customize:
- Test discovery patterns
- Output verbosity
- Markers
- Logging levels
- Coverage options

## Environment

Tests expect MCP server running at:
- **Default:** `http://localhost:8000`

Override with `BASE_URL` in test file if needed.

## Cleanup

Tests automatically clean up:
1. Created organizations (cascades to members, invites)
2. Created connections
3. Test user accounts

Run cleanup manually if tests fail:
```bash
pytest test_mcp_server.py::test_cleanup -v
pytest test_mcp_server.py::test_final_user_deletion -v
```

## Troubleshooting

### Tests fail to connect
- Ensure MCP server is running: `docker-compose up`
- Check URL: `http://localhost:8000/health`

### Resource cleanup fails
- Run cleanup tests manually
- Check database for orphaned test data

### Tests timeout
- Increase `TEST_TIMEOUT` in test file
- Check server performance

## Future Tests

- WordPress connection operations
- File upload (avatar/banner)
- Invite rejection
- Member role updates
- Organization member removal
- Remote WordPress setup
- Error handling edge cases
