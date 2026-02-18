#!/bin/bash
# Comprehensive MCP Server Integration Test Suite
# Acts as a browser to test all functionality

# Note: Don't use 'set -e' so we can collect all test results

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_SERVER_URL="${MCP_SERVER_URL:-http://localhost:8000}"
TEST_EMAIL="test-$(date +%s)@example.com"
TEST_PASSWORD="SecureTestPass123!"
TEST_NAME="Integration Test User"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results storage
SESSION_ID=""
USER_ID=""
CONNECTION_ID=""
POST_ID=""
PAGE_ID=""

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

log_error() {
    echo -e "${RED}✗ ${NC}$1"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

log_section() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_header=$4

    if [ -z "$auth_header" ]; then
        curl -s -X "$method" "$MCP_SERVER_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$MCP_SERVER_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-Session-ID: $SESSION_ID" \
            -d "$data"
    fi
}

mcp_tool_call() {
    local tool_name=$1
    local arguments=$2

    cat > /tmp/mcp_request.json <<EOF
{
  "jsonrpc": "2.0",
  "id": "test-$(date +%s)",
  "method": "tools/call",
  "params": {
    "name": "$tool_name",
    "arguments": $arguments
  }
}
EOF

    curl -s -X POST "$MCP_SERVER_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: $SESSION_ID" \
        -d @/tmp/mcp_request.json
}

# =============================================================================
# TEST SUITE
# =============================================================================

log_section "1. HEALTH CHECK"

log_info "Testing /health endpoint..."
health_response=$(curl -s "$MCP_SERVER_URL/health")
if echo "$health_response" | grep -q "alive.*true"; then
    log_success "Health check passed"
else
    log_error "Health check failed: $health_response"
fi

# =============================================================================
log_section "2. AUTHENTICATION TESTS"

# Test 2.1: User Registration
log_info "Testing user registration..."
register_response=$(api_call POST "/register" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"name\": \"$TEST_NAME\"
}")

USER_ID=$(echo "$register_response" | jq -r '.id')
if [ "$USER_ID" != "null" ] && [ -n "$USER_ID" ]; then
    log_success "Registration successful (User ID: $USER_ID)"
else
    log_error "Registration failed: $register_response"
fi

# Test 2.2: User Login
log_info "Testing user login..."
login_response=$(api_call POST "/login" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\"
}")

SESSION_ID=$(echo "$login_response" | jq -r '.session_id')
if [ "$SESSION_ID" != "null" ] && [ -n "$SESSION_ID" ]; then
    log_success "Login successful (Session ID: ${SESSION_ID:0:20}...)"
else
    log_error "Login failed: $login_response"
fi

# Test 2.3: Get Current User
log_info "Testing /me endpoint..."
me_response=$(curl -s -X GET "$MCP_SERVER_URL/api/auth/me" \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID")
user_email=$(echo "$me_response" | jq -r '.user.email' 2>/dev/null || echo "")
if [ "$user_email" = "$TEST_EMAIL" ]; then
    log_success "/me returned correct user"
else
    log_error "/me failed: $me_response"
fi

# =============================================================================
log_section "3. CONNECTION MANAGEMENT TESTS"

# Test 3.1: Create WordPress Connection
log_info "Testing connection creation..."
connection_response=$(api_call POST "/connections" "{
    \"name\": \"Test WordPress Connection\",
    \"wp_url\": \"http://wordpress:80\",
    \"wp_graphql_endpoint\": \"http://wordpress:80/graphql\",
    \"wp_user\": \"admin\",
    \"wp_app_password\": \"xxZBjQ1vnoOQElSlwNyaC4jD\"
}" "auth")

CONNECTION_ID=$(echo "$connection_response" | jq -r '.id')
if [ "$CONNECTION_ID" != "null" ] && [ -n "$CONNECTION_ID" ]; then
    log_success "Connection created (ID: $CONNECTION_ID)"
else
    log_error "Connection creation failed: $connection_response"
fi

# Test 3.2: List Connections
log_info "Testing list connections..."
connections_list=$(api_call GET "/connections" "" "auth")
connection_count=$(echo "$connections_list" | jq '. | length')
if [ "$connection_count" -gt 0 ]; then
    log_success "Found $connection_count connection(s)"
else
    log_error "List connections failed: $connections_list"
fi

# Test 3.3: Activate Connection
log_info "Testing connection activation..."
activate_response=$(curl -s -X POST "$MCP_SERVER_URL/connections/$CONNECTION_ID/activate" \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID")
if echo "$activate_response" | grep -q "success.*true"; then
    log_success "Connection activated"
else
    log_error "Connection activation failed: $activate_response"
fi

# =============================================================================
log_section "4. POST OPERATIONS TESTS"

# Test 4.1: Create Post
log_info "Testing create_post tool..."
create_post_response=$(mcp_tool_call "create_post" "{
    \"title\": \"Test Post $(date +%s)\",
    \"content\": \"This is a test post created by integration test suite.\",
    \"status\": \"draft\"
}")

POST_ID=$(echo "$create_post_response" | jq -r '.result.content[0].text' | grep -o '"id": [0-9]*' | head -1 | grep -o '[0-9]*')
if [ -n "$POST_ID" ]; then
    log_success "Post created (ID: $POST_ID)"
else
    log_error "Post creation failed: $create_post_response"
fi

# Test 4.2: Get Posts
log_info "Testing get_posts tool..."
get_posts_response=$(mcp_tool_call "get_posts" "{
    \"status\": \"any\",
    \"per_page\": 5
}")

if echo "$get_posts_response" | grep -q '"id"'; then
    log_success "get_posts returned results"
else
    log_error "get_posts failed: $get_posts_response"
fi

# Test 4.3: Get Single Post
if [ -n "$POST_ID" ]; then
    log_info "Testing get_post tool..."
    get_post_response=$(mcp_tool_call "get_post" "{\"post_id\": $POST_ID}")

    if echo "$get_post_response" | grep -q "\"title\""; then
        log_success "get_post returned correct post"
    else
        log_error "get_post failed: $get_post_response"
    fi
fi

# Test 4.4: Update Post
if [ -n "$POST_ID" ]; then
    log_info "Testing update_post tool..."
    update_post_response=$(mcp_tool_call "update_post" "{
        \"post_id\": $POST_ID,
        \"title\": \"Updated Test Post\",
        \"status\": \"publish\"
    }")

    if echo "$update_post_response" | grep -q "Updated Test Post"; then
        log_success "Post updated successfully"
    else
        log_error "Post update failed: $update_post_response"
    fi
fi

# =============================================================================
log_section "5. PAGE OPERATIONS TESTS"

# Test 5.1: Create Page
log_info "Testing create_page tool..."
create_page_response=$(mcp_tool_call "create_page" "{
    \"title\": \"Test Page $(date +%s)\",
    \"content\": \"This is a test page created by integration test suite.\",
    \"status\": \"draft\"
}")

PAGE_ID=$(echo "$create_page_response" | jq -r '.result.content[0].text' | grep -o '"id": [0-9]*' | head -1 | grep -o '[0-9]*')
if [ -n "$PAGE_ID" ]; then
    log_success "Page created (ID: $PAGE_ID)"
else
    log_error "Page creation failed: $create_page_response"
fi

# Test 5.2: Get Pages
log_info "Testing get_pages tool..."
get_pages_response=$(mcp_tool_call "get_pages" "{\"per_page\": 5}")

if echo "$get_pages_response" | grep -q '"id"'; then
    log_success "get_pages returned results"
else
    log_error "get_pages failed: $get_pages_response"
fi

# Test 5.3: Get Single Page
if [ -n "$PAGE_ID" ]; then
    log_info "Testing get_page tool..."
    get_page_response=$(mcp_tool_call "get_page" "{\"page_id\": $PAGE_ID}")

    if echo "$get_page_response" | grep -q "\"title\""; then
        log_success "get_page returned correct page"
    else
        log_error "get_page failed: $get_page_response"
    fi
fi

# Test 5.4: Update Page
if [ -n "$PAGE_ID" ]; then
    log_info "Testing update_page tool..."
    update_page_response=$(mcp_tool_call "update_page" "{
        \"page_id\": $PAGE_ID,
        \"title\": \"Updated Test Page\",
        \"status\": \"publish\"
    }")

    if echo "$update_page_response" | grep -q "Updated Test Page"; then
        log_success "Page updated successfully"
    else
        log_error "Page update failed: $update_page_response"
    fi
fi

# =============================================================================
log_section "6. CLEANUP & DELETION TESTS"

# Test 6.1: Delete Post
if [ -n "$POST_ID" ]; then
    log_info "Testing delete_post tool..."
    delete_post_response=$(mcp_tool_call "delete_post" "{\"post_id\": $POST_ID}")

    if echo "$delete_post_response" | grep -q "deleted.*true"; then
        log_success "Post deleted successfully"
    else
        log_error "Post deletion failed: $delete_post_response"
    fi
fi

# Test 6.2: Logout
log_info "Testing logout..."
logout_response=$(curl -s -X POST "$MCP_SERVER_URL/logout" \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID")
if echo "$logout_response" | grep -q "success\|message\|logout"; then
    log_success "Logout successful"
else
    log_error "Logout failed: $logout_response"
fi

# =============================================================================
log_section "TEST SUMMARY"

echo ""
echo "  Total Tests:  $TESTS_RUN"
echo -e "  ${GREEN}Passed:       $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed:       $TESTS_FAILED${NC}"
else
    echo "  Failed:       $TESTS_FAILED"
fi
echo ""

# Calculate percentage
if [ $TESTS_RUN -gt 0 ]; then
    pass_rate=$((TESTS_PASSED * 100 / TESTS_RUN))
    echo "  Pass Rate:    ${pass_rate}%"
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Exit with error if any tests failed
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    log_success "All tests passed! 🎉"
    exit 0
fi
