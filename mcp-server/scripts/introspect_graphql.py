#!/usr/bin/env python3
"""Fetch WordPress GraphQL schema via introspection."""

import json
import sys
import urllib.request
import urllib.parse

# GraphQL introspection query
INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          description
          type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                }
              }
            }
          }
          defaultValue
        }
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
      inputFields {
        name
        description
        type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
            }
          }
        }
        defaultValue
      }
      interfaces {
        kind
        name
      }
      enumValues(includeDeprecated: true) {
        name
        description
      }
      possibleTypes {
        kind
        name
      }
    }
  }
}
"""


def fetch_schema(graphql_url: str) -> dict:
    """Fetch GraphQL schema via introspection."""
    payload = json.dumps({"query": INTROSPECTION_QUERY}).encode('utf-8')

    req = urllib.request.Request(
        graphql_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            data = json.loads(response_data)

            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data["data"]["__schema"]
    except urllib.error.HTTPError as e:
        raise Exception(f"GraphQL introspection failed: {e.code} {e.read().decode('utf-8')}")


if __name__ == "__main__":
    graphql_url = sys.argv[1] if len(sys.argv) > 1 else "http://wordpress:80/graphql"

    try:
        schema = fetch_schema(graphql_url)
        print(json.dumps(schema, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
