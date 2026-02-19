"""Async GraphQL client for WPGraphQL with caching support."""

import hashlib
import json
import logging
from typing import Any, TYPE_CHECKING, cast

import httpx

if TYPE_CHECKING:
    from wp_mcp.cache import CacheManager

from wp_mcp.config import config

logger = logging.getLogger(__name__)


class GraphQLClient:
    """Async client for communicating with the WPGraphQL endpoint with Redis caching."""

    def __init__(
        self,
        endpoint: str | None = None,
        auth: tuple[str, str] | None = None
    ) -> None:
        """Initialize GraphQL client with connection-specific credentials.

        Args:
            endpoint: GraphQL endpoint URL. If None, uses config default.
            auth: (username, password) tuple. If None, uses config default.
        """
        self._endpoint = endpoint or config.wp_graphql_endpoint
        self._auth = auth or config.wp_auth
        self._cache: CacheManager | None = None

    def _get_cache_key(
        self, query: str, variables: dict[str, Any] | None = None, user_id: int | None = None
    ) -> str:
        """Generate cache key from query, variables, and user context.

        Args:
            query: GraphQL query string
            variables: Query variables
            user_id: User ID for cache isolation (prevents cross-user cache sharing)

        Returns:
            Cache key string
        """
        # Create deterministic hash from query + variables + user context
        # Use SHA256 instead of MD5 to avoid collision attacks
        content = query + json.dumps(variables or {}, sort_keys=True)

        # Include user_id to isolate cache per user
        if user_id is not None:
            content = f"user:{user_id}:" + content

        query_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"gql:{query_hash}"

    def _extract_cache_ttl(self, query: str) -> int:
        """Determine cache TTL based on query type.

        Args:
            query: GraphQL query string

        Returns:
            TTL in seconds
        """
        query_lower = query.lower()

        # Short TTL for frequently updated data
        if "revisions" in query_lower:
            return 60  # 1 minute

        # Medium TTL for posts/pages
        if any(x in query_lower for x in ["post", "page"]):
            return 300  # 5 minutes

        # Longer TTL for categories/tags
        if any(x in query_lower for x in ["categories", "tags", "media"]):
            return 600  # 10 minutes

        # Default TTL
        return 300  # 5 minutes

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation.

        Args:
            query: The GraphQL query/mutation string.
            variables: Optional variables for the query.

        Returns:
            The 'data' portion of the GraphQL response.

        Raises:
            GraphQLError: If the response contains errors.
            httpx.HTTPError: If the HTTP request fails.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._endpoint,
                json=payload,
                auth=self._auth,  # type: ignore[arg-type]
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        result = response.json()

        if "errors" in result:
            error_messages = [e.get("message", "Unknown error") for e in result["errors"]]
            raise GraphQLError("; ".join(error_messages), errors=result["errors"])

        return cast(dict[str, Any], result.get("data", {}))

    async def query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        use_cache: bool = True,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query with caching support.

        Args:
            query: GraphQL query string
            variables: Query variables
            use_cache: Whether to use cache (default True)

        Returns:
            Query result data
        """
        # Try cache first
        if use_cache:
            if self._cache is None:
                from wp_mcp.cache import cache
                self._cache = cache

            cache_key = self._get_cache_key(query, variables, user_id)
            cached_result = await self._cache.get(cache_key)

            if cached_result is not None:
                return cast(dict[str, Any], cached_result)

        # Execute query
        result = await self.execute(query, variables)

        # Cache the result with user isolation
        if use_cache and result:
            cache_key = self._get_cache_key(query, variables, user_id)
            ttl = self._extract_cache_ttl(query)
            await self._cache.set(cache_key, result, ttl=ttl)

        return result

    async def mutate(
        self,
        mutation: str,
        variables: dict[str, Any] | None = None,
        invalidate_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL mutation and invalidate related cache.

        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            invalidate_patterns: Cache key patterns to invalidate (e.g., ["gql:*post*"])

        Returns:
            Mutation result data
        """
        # Execute mutation (never cached)
        result = await self.execute(mutation, variables)

        # Invalidate related cache entries
        if invalidate_patterns:
            if self._cache is None:
                from wp_mcp.cache import cache
                self._cache = cache

            for pattern in invalidate_patterns:
                await self._cache.invalidate_pattern(pattern)
                logger.debug("Invalidated cache pattern: %s", pattern)

        return result


class GraphQLError(Exception):
    """Error returned by the GraphQL endpoint."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


# Legacy singleton client instance (uses environment variables)
# DEPRECATED: Use get_graphql_client() instead for multi-tenancy support
gql_client = GraphQLClient()


async def get_graphql_client(connection_id: int, user_id: int) -> GraphQLClient:
    """Get GraphQL client for a specific user connection.

    This function retrieves the connection from the database and creates
    a GraphQL client with the connection-specific credentials.

    Args:
        connection_id: ID of the WordPress connection
        user_id: ID of the user who owns the connection

    Returns:
        GraphQLClient configured for the specified connection

    Raises:
        ValueError: If connection not found or user doesn't have access
    """
    from wp_mcp.connection_manager import connection_manager

    # Get connection from database (includes decrypted credentials)
    connection = await connection_manager.get_connection(connection_id, user_id)

    if not connection:
        raise ValueError(f"Connection {connection_id} not found for user {user_id}")

    # Create client with connection-specific credentials
    return GraphQLClient(
        endpoint=connection["wp_graphql_endpoint"],
        auth=(connection["wp_user"], connection["wp_app_password"])
    )
