"""Auto-generated MCP tools from WordPress GraphQL schema.
DO NOT EDIT MANUALLY - regenerate using generate_mcp_from_graphql.py
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.context_helper import get_connection_info


def register(mcp: FastMCP) -> None:
    """Register auto-generated GraphQL tools with the MCP server."""


    # QUERY: contentNode
    @mcp.tool()
    async def contentNode(
        id: str,
        idType: Any | None = None,
        contentType: Any | None = None,
        asPreview: bool | None = None,
        context: dict | None = None
    ) -> dict[str, Any]:
        """A node used to manage content"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """query Contentnode($id: ID!, $idType: ContentNodeIdTypeEnum, $contentType: ContentTypeEnum, $asPreview: Boolean) {
  contentNode(id: $id, idType: $idType, contentType: $contentType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"id": id, "idType": idType, "contentType": contentType, "asPreview": asPreview}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("contentNode", {})


    # QUERY: page
    @mcp.tool()
    async def page(
        id: str,
        idType: Any | None = None,
        asPreview: bool | None = None,
        context: dict | None = None
    ) -> dict[str, Any]:
        """An object of the page Type. """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """query Page($id: ID!, $idType: PageIdType, $asPreview: Boolean) {
  page(id: $id, idType: $idType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"id": id, "idType": idType, "asPreview": asPreview}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("page", {})


    # QUERY: pages
    @mcp.tool()
    async def pages(
        first: int | None = None,
        last: int | None = None,
        after: str | None = None,
        before: str | None = None,
        where: Any | None = None,
        context: dict | None = None
    ) -> dict[str, Any]:
        """Connection between the RootQuery type and the page type"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """query Pages($first: Int, $last: Int, $after: String, $before: String, $where: RootQueryToPageConnectionWhereArgs) {
  pages(first: $first, last: $last, after: $after, before: $before, where: $where) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"first": first, "last": last, "after": after, "before": before, "where": where}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("pages", {})


    # QUERY: post
    @mcp.tool()
    async def post(
        id: str,
        idType: Any | None = None,
        asPreview: bool | None = None,
        context: dict | None = None
    ) -> dict[str, Any]:
        """An object of the post Type. """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """query Post($id: ID!, $idType: PostIdType, $asPreview: Boolean) {
  post(id: $id, idType: $idType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"id": id, "idType": idType, "asPreview": asPreview}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("post", {})


    # QUERY: posts
    @mcp.tool()
    async def posts(
        first: int | None = None,
        last: int | None = None,
        after: str | None = None,
        before: str | None = None,
        where: Any | None = None,
        context: dict | None = None
    ) -> dict[str, Any]:
        """Connection between the RootQuery type and the post type"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """query Posts($first: Int, $last: Int, $after: String, $before: String, $where: RootQueryToPostConnectionWhereArgs) {
  posts(first: $first, last: $last, after: $after, before: $before, where: $where) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"first": first, "last": last, "after": after, "before": before, "where": where}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("posts", {})


    # MUTATION: createPage
    @mcp.tool()
    async def createPage(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The createPage mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Createpage($input: CreatePageInput!) {
  createPage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("createPage", {})


    # MUTATION: createPost
    @mcp.tool()
    async def createPost(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The createPost mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Createpost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("createPost", {})


    # MUTATION: deletePage
    @mcp.tool()
    async def deletePage(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The deletePage mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Deletepage($input: DeletePageInput!) {
  deletePage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("deletePage", {})


    # MUTATION: deletePost
    @mcp.tool()
    async def deletePost(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The deletePost mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Deletepost($input: DeletePostInput!) {
  deletePost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("deletePost", {})


    # MUTATION: updatePage
    @mcp.tool()
    async def updatePage(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The updatePage mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Updatepage($input: UpdatePageInput!) {
  updatePage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("updatePage", {})


    # MUTATION: updatePost
    @mcp.tool()
    async def updatePost(
        input: Any,
        context: dict | None = None
    ) -> dict[str, Any]:
        """The updatePost mutation"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """mutation Updatepost($input: UpdatePostInput!) {
  updatePost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}"""

        variables = {"input": input}

        data = await client.query(
            query,
            variables={k: v for k, v in variables.items() if v is not None},
            user_id=user_id,
        )

        return data.get("updatePost", {})

