#!/usr/bin/env python3
"""Generate MCP tools from WordPress GraphQL schema.

This script analyzes the WordPress GraphQL schema and automatically generates:
- Python MCP tool functions
- GraphQL queries and mutations
- Response type mappings

Usage:
    python generate_mcp_from_graphql.py [--schema schema.json] [--output src/wp_mcp/tools/generated]
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any


def parse_type(type_obj: dict) -> tuple[str, bool]:
    """Parse GraphQL type object and return (type_name, is_required)."""
    if type_obj["kind"] == "NON_NULL":
        inner_type, _ = parse_type(type_obj["ofType"])
        return inner_type, True
    elif type_obj["kind"] == "LIST":
        inner_type, required = parse_type(type_obj["ofType"])
        return f"List[{inner_type}]", False
    else:
        return type_obj["name"], False


def graphql_type_to_python(type_name: str) -> str:
    """Convert GraphQL scalar types to Python types."""
    type_map = {
        "String": "str",
        "Int": "int",
        "Float": "float",
        "Boolean": "bool",
        "ID": "str",
    }
    return type_map.get(type_name, "Any")


def generate_query_string(field: dict, type_name: str) -> str:
    """Generate GraphQL query/mutation string."""
    # Build argument list
    args = []
    for arg in field.get("args", []):
        arg_type, required = parse_type(arg["type"])
        if required:
            args.append(f"${arg['name']}: {arg_type}!")
        else:
            args.append(f"${arg['name']}: {arg_type}")

    args_str = ", ".join(args) if args else ""

    # Build field arguments
    field_args = [f"{arg['name']}: ${arg['name']}" for arg in field.get("args", [])]
    field_args_str = f"({', '.join(field_args)})" if field_args else ""

    # Determine what fields to return (simplified - returns common fields)
    if type_name == "Query":
        query_type = "query"
    else:
        query_type = "mutation"

    return f"""
{query_type} {field['name'].capitalize()}({args_str}) {{
  {field['name']}{field_args_str} {{
    ... on Post {{
      databaseId
      title
      slug
      status
      content
      date
      modified
    }}
    ... on Page {{
      databaseId
      title
      slug
      status
      content
      date
      modified
    }}
  }}
}}
""".strip()


def generate_tool_function(field: dict, query_str: str) -> str:
    """Generate Python MCP tool function."""
    func_name = field["name"]
    description = field.get("description", f"Execute {func_name} GraphQL operation")

    # Build function parameters
    params = []
    for arg in field.get("args", []):
        arg_type, required = parse_type(arg["type"])
        py_type = graphql_type_to_python(arg_type.replace("List[", "").replace("]", ""))

        if "List" in arg_type:
            py_type = f"list[{py_type}]"

        if required:
            params.append(f"{arg['name']}: {py_type}")
        else:
            params.append(f"{arg['name']}: {py_type} | None = None")

    params.append("context: dict | None = None")
    params_str = ",\n        ".join(params)

    # Build variables dict
    var_assignments = []
    for arg in field.get("args", []):
        var_assignments.append(f'"{arg["name"]}": {arg["name"]}')

    variables_str = ", ".join(var_assignments) if var_assignments else ""

    return f'''
    @mcp.tool()
    async def {func_name}(
        {params_str}
    ) -> dict[str, Any]:
        """{description}"""
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        query = """{query_str}"""

        variables = {{{variables_str}}}

        data = await client.query(
            query,
            variables={{k: v for k, v in variables.items() if v is not None}},
            user_id=user_id,
        )

        return data.get("{func_name}", {{}})
'''.strip()


def generate_mcp_tools(schema: dict, output_dir: Path):
    """Generate MCP tools from GraphQL schema."""
    query_type = None
    mutation_type = None

    # Find Query and Mutation types
    for type_obj in schema["types"]:
        if type_obj["name"] == schema["queryType"]["name"]:
            query_type = type_obj
        elif schema.get("mutationType") and type_obj["name"] == schema["mutationType"]["name"]:
            mutation_type = type_obj

    if not query_type:
        raise Exception("Query type not found in schema")

    # Generate tools for interesting queries and mutations
    interesting_queries = ["post", "page", "posts", "pages", "contentNode"]
    interesting_mutations = ["createPost", "updatePost", "deletePost", "createPage", "updatePage", "deletePage"]

    generated_tools = []

    # Generate query tools
    if query_type and query_type.get("fields"):
        for field in query_type["fields"]:
            if field["name"] in interesting_queries:
                query_str = generate_query_string(field, "Query")
                tool_func = generate_tool_function(field, query_str)
                generated_tools.append({
                    "name": field["name"],
                    "type": "query",
                    "function": tool_func,
                    "query": query_str
                })

    # Generate mutation tools
    if mutation_type and mutation_type.get("fields"):
        for field in mutation_type["fields"]:
            if field["name"] in interesting_mutations:
                query_str = generate_query_string(field, "Mutation")
                tool_func = generate_tool_function(field, query_str)
                generated_tools.append({
                    "name": field["name"],
                    "type": "mutation",
                    "function": tool_func,
                    "query": query_str
                })

    # Write generated tools to file
    output_file = output_dir / "generated_tools.py"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write('''"""Auto-generated MCP tools from WordPress GraphQL schema.
DO NOT EDIT MANUALLY - regenerate using generate_mcp_from_graphql.py
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.context_helper import get_connection_info


def register(mcp: FastMCP) -> None:
    """Register auto-generated GraphQL tools with the MCP server."""

''')

        for tool in generated_tools:
            f.write(f"\n    # {tool['type'].upper()}: {tool['name']}\n")
            f.write(f"    {tool['function']}\n\n")

    # Also write the queries to a separate file for reference
    queries_file = output_dir / "generated_queries.py"
    with open(queries_file, "w") as f:
        f.write('"""Auto-generated GraphQL queries from WordPress schema."""\n\n')
        for tool in generated_tools:
            f.write(f'{tool["name"].upper()}_QUERY = """\n{tool["query"]}\n"""\n\n')

    print(f"✅ Generated {len(generated_tools)} MCP tools")
    print(f"   Output: {output_file}")
    print(f"   Queries: {queries_file}")

    return generated_tools


def main():
    parser = argparse.ArgumentParser(description="Generate MCP tools from WordPress GraphQL schema")
    parser.add_argument("--schema", default="schema.json", help="Path to GraphQL schema JSON file")
    parser.add_argument("--output", default="src/wp_mcp/tools/generated", help="Output directory")
    parser.add_argument("--graphql-url", help="WordPress GraphQL endpoint URL (for live introspection)")

    args = parser.parse_args()

    # If GraphQL URL is provided, fetch schema first
    if args.graphql_url:
        from introspect_graphql import fetch_schema
        print(f"Fetching schema from {args.graphql_url}...")
        schema = fetch_schema(args.graphql_url)
    else:
        # Load schema from file
        with open(args.schema) as f:
            schema_data = json.load(f)
            # Handle both direct schema and wrapped schema
            schema = schema_data if "types" in schema_data else schema_data.get("__schema", schema_data)

    output_dir = Path(args.output)
    generate_mcp_tools(schema, output_dir)


if __name__ == "__main__":
    main()
