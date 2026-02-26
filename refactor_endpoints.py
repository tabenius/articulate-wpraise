#!/usr/bin/env python3
"""Script to refactor remaining authenticated endpoints."""

import re

# Read the server.py file
with open('/home/xyzzy/wp-ai/mcp-server/src/articulate_mcp/server.py', 'r') as f:
    content = f.read()

# Pattern to match authenticated endpoints
# Matches: async def ENDPOINT_NAME(request):
#          ...auth check code...
pattern = re.compile(
    r'(async def (\w+_endpoint)\(request\):.*?)'  # Function signature
    r'(from articulate_mcp\.user_manager import UserManager\n.*?)'  # UserManager import
    r'(try:\n\s+session_id = request\.headers\.get\("X-Session-ID"\)\n'  # Auth code start
    r'\s+if not session_id:\n'
    r'\s+return JSONResponse\(\{"error": "Session required"\}, status_code=401\)\n\n'
    r'\s+user = await UserManager\.get_user_from_session\(session_id\)\n'
    r'\s+if not user:\n'
    r'\s+return JSONResponse\(\{"error": "Invalid session"\}, status_code=401\)\n\n)',  # Auth code end
    re.DOTALL
)

def refactor_match(match):
    """Refactor a matched endpoint."""
    before = match.group(1)  # Function signature and docstring
    func_name = match.group(2)
    user_manager_import = match.group(3)
    auth_code = match.group(4)

    # Remove UserManager import line
    before_clean = user_manager_import.replace('from articulate_mcp.user_manager import UserManager\n    ', '')

    # Add decorator before function
    refactored = f'@require_auth\n{before}{before_clean}try:\n        user = request.state.user\n\n'

    return refactored

# Find how many matches we have
matches = list(pattern.finditer(content))
print(f"Found {len(matches)} endpoints to refactor")

# Show which endpoints will be refactored
for match in matches:
    print(f"  - {match.group(2)}")
