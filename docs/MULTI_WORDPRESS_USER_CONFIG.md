# Multi-WordPress User Configuration

## Overview

Enable users to configure and manage multiple WordPress site connections from a single Articulate instance. Each user can:
- Add multiple WordPress sites (personal blog, client sites, etc.)
- Switch between WordPress sites
- Manage site credentials securely
- Collaborate on shared sites (future)

This is **not full multi-tenancy** - it's user-level WordPress connection management.

---

## Architecture

### Database Schema

**Users Table** (`users`):
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**WordPress Connections Table** (`wordpress_connections`):
```sql
CREATE TABLE wordpress_connections (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL, -- "My Personal Blog"
  wp_url VARCHAR(500) NOT NULL,
  wp_graphql_endpoint VARCHAR(500) NOT NULL,
  wp_user VARCHAR(255) NOT NULL,
  wp_app_password TEXT NOT NULL, -- Encrypted
  is_active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, name)
);

CREATE INDEX idx_wp_connections_user_id ON wordpress_connections(user_id);
CREATE INDEX idx_wp_connections_active ON wordpress_connections(user_id, is_active);
```

**Sessions Table** (`sessions`):
```sql
CREATE TABLE sessions (
  id VARCHAR(255) PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

---

## Backend Implementation

### 1. Database Setup

**Location**: `/mcp-server/migrations/004-user-wordpress-connections.sql`

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- WordPress connections
CREATE TABLE IF NOT EXISTS wordpress_connections (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  wp_url VARCHAR(500) NOT NULL,
  wp_graphql_endpoint VARCHAR(500) NOT NULL,
  wp_user VARCHAR(255) NOT NULL,
  wp_app_password TEXT NOT NULL,
  is_active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, name)
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
  id VARCHAR(255) PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wp_connections_user_id ON wordpress_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_wp_connections_active ON wordpress_connections(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
```

### 2. User Management Module

**Location**: `/mcp-server/src/wp_mcp/user_manager.py`

```python
class UserManager:
    """Manage users and authentication."""

    async def register_user(email: str, password: str, name: str) -> User
    async def authenticate(email: str, password: str) -> Session
    async def get_user(user_id: int) -> User
    async def logout(session_id: str)
```

### 3. WordPress Connection Manager

**Location**: `/mcp-server/src/wp_mcp/connection_manager.py`

```python
class ConnectionManager:
    """Manage user WordPress connections."""

    async def add_connection(user_id, name, wp_url, wp_user, wp_app_password) -> Connection
    async def get_connections(user_id) -> list[Connection]
    async def get_active_connection(user_id) -> Connection
    async def set_active_connection(user_id, connection_id)
    async def update_connection(connection_id, **updates)
    async def delete_connection(connection_id)
    async def test_connection(connection_id) -> bool
```

### 4. Dynamic GraphQL Client

**Location**: Update `/mcp-server/src/wp_mcp/graphql/client.py`

```python
class GraphQLClient:
    def __init__(self, connection: WordPressConnection | None = None):
        """Initialize with optional user connection."""
        if connection:
            self._endpoint = connection.wp_graphql_endpoint
            self._auth = (connection.wp_user, connection.wp_app_password)
        else:
            # Fall back to config (backward compatible)
            self._endpoint = config.wp_graphql_endpoint
            self._auth = config.wp_auth
```

### 5. Context Middleware

**Location**: `/mcp-server/src/wp_mcp/middleware/auth.py`

```python
class AuthMiddleware:
    """Extract user from session and inject connection."""

    async def __call__(self, request):
        session_id = request.headers.get("X-Session-ID")
        user = await get_user_from_session(session_id)

        if user:
            connection = await get_active_connection(user.id)
            request.state.user = user
            request.state.wp_connection = connection

        return await self.app(request)
```

### 6. API Routes

**Location**: `/web/src/app/api/`

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/connections` - List user's WordPress connections
- `POST /api/connections` - Add new connection
- `GET /api/connections/:id` - Get connection details
- `PUT /api/connections/:id` - Update connection
- `DELETE /api/connections/:id` - Delete connection
- `POST /api/connections/:id/activate` - Set as active connection
- `POST /api/connections/:id/test` - Test connection

---

## Frontend Implementation

### 1. Auth Context

**Location**: `/web/src/contexts/auth-context.tsx`

```typescript
interface AuthContext {
  user: User | null;
  session: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}
```

### 2. Connection Context

**Location**: `/web/src/contexts/connection-context.tsx`

```typescript
interface ConnectionContext {
  connections: WordPressConnection[];
  activeConnection: WordPressConnection | null;
  addConnection: (data: ConnectionData) => Promise<void>;
  updateConnection: (id: number, data: Partial<ConnectionData>) => Promise<void>;
  deleteConnection: (id: number) => Promise<void>;
  setActive: (id: number) => Promise<void>;
  testConnection: (id: number) => Promise<boolean>;
}
```

### 3. Login/Register Page

**Location**: `/web/src/app/(auth)/login/page.tsx`

- Email/password form
- Login button
- "Create account" link
- Redirect to connections page after login

### 4. Connections Management Page

**Location**: `/web/src/app/connections/page.tsx`

- List of all user's WordPress connections
- "Add New Connection" button
- Card for each connection with:
  - Connection name
  - WordPress URL
  - Active indicator
  - Edit/Delete/Activate buttons
  - Test connection button

### 5. Connection Form Modal

**Location**: `/web/src/components/connections/connection-form.tsx`

Form fields:
- Connection name (e.g., "My Blog")
- WordPress URL
- WordPress username
- Application password
- Test connection button
- Save button

### 6. Connection Switcher

**Location**: `/web/src/components/layout/connection-switcher.tsx`

- Dropdown in header
- Shows active connection name
- Click to see all connections
- Quick switch between connections

### 7. Protected Routes

**Location**: `/web/src/middleware.ts`

```typescript
export function middleware(request: NextRequest) {
  const session = request.cookies.get('session');

  if (!session && !request.url.includes('/login')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Add session header for API calls
  const requestHeaders = new Headers(request.headers);
  if (session) {
    requestHeaders.set('X-Session-ID', session.value);
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}
```

---

## Security Considerations

### 1. Password Storage
- Use bcrypt for user passwords (12 rounds)
- Never store in plaintext

### 2. Application Password Encryption
- Encrypt WordPress app passwords at rest
- Use AES-256-GCM with unique key per environment
- Key stored in environment variable `ENCRYPTION_KEY`

### 3. Session Management
- Generate cryptographically secure session IDs
- 7-day expiration
- HTTP-only cookies
- CSRF protection

### 4. Connection Validation
- Test connection before saving
- Validate WordPress URL format
- Check GraphQL endpoint accessibility
- Verify credentials work

---

## Migration Path

### For Existing Single-User Setup

1. **Create default user**:
   ```sql
   INSERT INTO users (email, password_hash, name)
   VALUES ('admin@localhost', 'temp_hash', 'Admin');
   ```

2. **Migrate current WordPress config**:
   ```sql
   INSERT INTO wordpress_connections (
     user_id, name, wp_url, wp_graphql_endpoint,
     wp_user, wp_app_password, is_active
   )
   VALUES (
     1, 'Default WordPress',
     'http://localhost:8080', 'http://localhost:8080/graphql',
     'admin', 'from_env', true
   );
   ```

3. **Feature flag**: `MULTI_USER_MODE=true`

---

## Implementation Timeline

### Week 1: Backend Foundation
- Database schema and migrations
- User authentication (register/login/logout)
- Session management
- Connection CRUD operations

### Week 2: Frontend UI
- Login/register pages
- Connections management page
- Connection form modal
- Connection switcher component

### Week 3: Integration
- Dynamic GraphQL client
- Auth middleware
- Protected routes
- Session handling in API calls

### Week 4: Polish & Testing
- Test connection functionality
- Error handling
- Loading states
- End-to-end testing

---

## Testing

### Backend Tests
```bash
# Test user registration
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "secure123",
  "name": "John Doe"
}

# Test login
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "secure123"
}
# Returns session ID

# Test add connection
POST /api/connections
Headers: X-Session-ID: <session>
{
  "name": "My Blog",
  "wp_url": "https://myblog.com",
  "wp_user": "admin",
  "wp_app_password": "xxxx"
}

# Test switch connection
POST /api/connections/1/activate
Headers: X-Session-ID: <session>

# Verify posts come from active connection
GET /api/posts
Headers: X-Session-ID: <session>
```

### Frontend Tests
1. Register new user
2. Add WordPress connection
3. Test connection (should show success/error)
4. Activate connection
5. Create post (should go to active WordPress)
6. Add second connection
7. Switch connections
8. Verify posts change

---

## Future Enhancements

- **Connection sharing**: Allow multiple users to access same WordPress
- **Role-based access**: Admin, Editor, Author per connection
- **Connection groups**: Organize connections by client/project
- **Auto-sync**: Periodically test all connections
- **Connection health**: Monitor uptime and performance
- **Batch operations**: Bulk post across multiple WordPress sites

---

This architecture provides secure, scalable per-user WordPress management while maintaining backward compatibility with single-user setups.
