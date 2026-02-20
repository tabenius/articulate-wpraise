"""MCP tools for WordPress template and template part operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.context_helper import get_connection_info
from wp_mcp.graphql.client import get_graphql_client


def register(mcp: FastMCP) -> None:
    """Register template tools with the MCP server."""

    @mcp.tool()
    async def get_templates(
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Get all block templates for the active theme.

        Returns a list of templates with their content, title, slug, and metadata.
        Templates are reusable page layouts (like index, single, page, etc.).
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """
        query GetTemplates {
          templates: __type(name: "RootQuery") {
            fields {
              name
              description
            }
          }
        }
        """

        # For now, we'll use a direct GraphQL query to get wp_template posts
        # WordPress stores templates as the wp_template post type
        query = """
        query GetTemplates($first: Int) {
          contentNodes(
            first: $first
            where: {contentTypes: ["wp_template"]}
          ) {
            nodes {
              ... on NodeWithTitle {
                title
              }
              ... on NodeWithContentEditor {
                content
              }
              databaseId
              slug
            }
          }
        }
        """

        data = await client.query(
            query,
            variables={"first": 100},
            user_id=user_id,
        )

        templates = data.get("contentNodes", {}).get("nodes", [])

        return [
            {
                "id": t.get("databaseId"),
                "title": t.get("title", ""),
                "slug": t.get("slug", ""),
                "content": t.get("content", ""),
            }
            for t in templates
        ]

    @mcp.tool()
    async def get_template(
        template_id: int,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get a single template by ID.

        Args:
            template_id: The database ID of the template

        Returns:
            Template data including content, title, slug, and metadata.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """
        query GetTemplate($id: ID!) {
          contentNode(id: $id, idType: DATABASE_ID) {
            ... on NodeWithTitle {
              title
            }
            ... on NodeWithContentEditor {
              content
            }
            databaseId
            slug
          }
        }
        """

        data = await client.query(
            query,
            variables={"id": str(template_id)},
            user_id=user_id,
        )

        template = data.get("contentNode", {})

        return {
            "id": template.get("databaseId"),
            "title": template.get("title", ""),
            "slug": template.get("slug", ""),
            "content": template.get("content", ""),
        }

    @mcp.tool()
    async def update_template(
        template_id: int,
        content: str,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Update a template's content.

        Args:
            template_id: The database ID of the template
            content: The new HTML/block content for the template

        Returns:
            Updated template data.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        # WordPress doesn't have a built-in mutation for wp_template in WPGraphQL
        # We'll need to use the REST API via a custom mutation
        # For now, return a placeholder

        return {
            "success": False,
            "message": "Template updates via GraphQL not yet supported. Use REST API.",
            "template_id": template_id,
        }

    @mcp.tool()
    async def get_template_parts(
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Get all template parts (header, footer, sidebar, etc.).

        Returns a list of template parts with their content and metadata.
        Template parts are reusable components used within templates.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        # WordPress stores template parts as wp_template_part post type
        query = """
        query GetTemplateParts($first: Int) {
          contentNodes(
            first: $first
            where: {contentTypes: ["wp_template_part"]}
          ) {
            nodes {
              ... on NodeWithTitle {
                title
              }
              ... on NodeWithContentEditor {
                content
              }
              databaseId
              slug
            }
          }
        }
        """

        data = await client.query(
            query,
            variables={"first": 100},
            user_id=user_id,
        )

        parts = data.get("contentNodes", {}).get("nodes", [])

        return [
            {
                "id": p.get("databaseId"),
                "title": p.get("title", ""),
                "slug": p.get("slug", ""),
                "content": p.get("content", ""),
            }
            for p in parts
        ]

    @mcp.tool()
    async def get_global_styles(
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get the theme's global styles (theme.json).

        Returns global style settings including colors, typography, spacing, etc.
        This is the theme.json configuration for Full Site Editing.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        # Global styles are stored as wp_global_styles post type
        # This is a complex feature that may need REST API access

        return {
            "success": False,
            "message": "Global styles retrieval not yet implemented. Use WordPress REST API.",
        }
