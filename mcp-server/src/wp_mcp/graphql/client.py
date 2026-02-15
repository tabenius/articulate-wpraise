"""Async GraphQL client for WPGraphQL."""

from typing import Any

import httpx

from wp_mcp.config import config


class GraphQLClient:
    """Async client for communicating with the WPGraphQL endpoint."""

    def __init__(self) -> None:
        self._endpoint = config.wp_graphql_endpoint
        self._auth = config.wp_auth

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
                auth=self._auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

        result = response.json()

        if "errors" in result:
            error_messages = [e.get("message", "Unknown error") for e in result["errors"]]
            raise GraphQLError("; ".join(error_messages), errors=result["errors"])

        return result.get("data", {})

    async def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query."""
        return await self.execute(query, variables)

    async def mutate(self, mutation: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL mutation."""
        return await self.execute(mutation, variables)


class GraphQLError(Exception):
    """Error returned by the GraphQL endpoint."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


# Singleton client instance
gql_client = GraphQLClient()
