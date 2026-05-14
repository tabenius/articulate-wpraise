/**
 * MCP HTTP client for communicating with the WordPress MCP server.
 *
 * The MCP server runs as a Docker container with streamable-http transport.
 * This client calls tools on the MCP server via JSON-RPC over HTTP.
 */

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";
export type MCPAccessTag = "Read" | "Create" | "Update" | "Delete";
const IS_PROD_OR_BUILD = process.env.NODE_ENV === "production";

interface ToolCallResult {
  content: Array<{
    type: string;
    text?: string;
  }>;
  isError?: boolean;
}

interface MCPToolResponse {
  result?: ToolCallResult;
  error?: { code: number; message: string };
}

interface MCPCallOptions {
  allowedAccess?: MCPAccessTag[];
  requestId?: string;
  idempotencyKey?: string;
  retries?: number;
}

function isLikelyGraphQLError(message: string): boolean {
  const m = message.toLowerCase();
  return (
    m.includes("graphql") ||
    m.includes("cannot query field") ||
    m.includes("syntax error") ||
    m.includes("variable") ||
    m.includes("mutation")
  );
}

function logGraphQLDiagnostics(context: string, detail: unknown): void {
  console.error(`[MCP/GraphQL] ${context}`, detail);
  console.error(
    "[MCP/GraphQL] Possible causes: invalid wp_graphql_endpoint, WPGraphQL plugin missing/disabled, bad app password, insufficient WP capabilities, schema mismatch, or upstream WordPress/network outage."
  );
  if (IS_PROD_OR_BUILD) {
    console.warn(
      "[MCP/GraphQL] Warning in production/build context. If this appears during `next build`, verify environment variables and WordPress connectivity used at build time."
    );
  }
}

function isSensibleToolPayload(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return true;
  if (typeof value === "object") return Object.keys(value as Record<string, unknown>).length > 0;
  return true;
}

/**
 * Call a tool on the MCP server via the streamable-http transport.
 */
export async function callMCPTool(
  name: string,
  args: Record<string, unknown>,
  authHeaders?: Record<string, string>,
  options?: MCPCallOptions
): Promise<unknown> {
  const maxRetries = options?.retries ?? 2;
  let attempt = 0;
  let lastError: Error | null = null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
    "X-Request-ID": options?.requestId || crypto.randomUUID(),
  };
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  // Forward authentication headers if provided
  if (authHeaders) {
    Object.assign(headers, authHeaders);
  }

  while (attempt <= maxRetries) {
    try {
      const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: crypto.randomUUID(),
          method: "tools/call",
          params: {
            name,
            arguments: args,
            ...(options?.allowedAccess ? { permissions: { allowedAccess: options.allowedAccess } } : {}),
          },
        }),
      });

      if (!response.ok) {
        const shouldRetry = response.status >= 500 || response.status === 429;
        if (shouldRetry && attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
          attempt += 1;
          continue;
        }
        throw new Error(`MCP server error: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get("content-type") || "";

      // Handle SSE response (streamable-http may respond with event stream)
      if (contentType.includes("text/event-stream")) {
        return await parseSSEResponse(response);
      }

      // Handle direct JSON response
      const data: MCPToolResponse = await response.json();

      if (data.error) {
        if (isLikelyGraphQLError(data.error.message)) {
          logGraphQLDiagnostics("GraphQL error returned from MCP tool", {
            tool: name,
            message: data.error.message,
            code: data.error.code,
          });
        }
        throw new Error(`MCP tool error: ${data.error.message}`);
      }

      // Extract the text content from MCP tool result
      const result = data.result;

      if (result?.content) {
        const textItems = result.content.filter((c) => c.type === "text" && c.text);

        if (textItems.length > 1) {
          // Multiple text items: parse each and combine into array
          const items = textItems.map((item) => {
            try { return JSON.parse(item.text!); } catch { return item.text; }
          });
          if (!isSensibleToolPayload(items)) {
            logGraphQLDiagnostics("Tool returned non-sensical multi-item payload", { tool: name, items });
          }
          return items;
        }

        if (textItems.length === 1) {
          try {
            const parsed = JSON.parse(textItems[0].text!);
            if (!isSensibleToolPayload(parsed)) {
              logGraphQLDiagnostics("Tool returned non-sensical parsed payload", { tool: name, parsed });
            }
            return parsed;
          } catch {
            const raw = textItems[0].text;
            if (!isSensibleToolPayload(raw)) {
              logGraphQLDiagnostics("Tool returned empty/unusable text payload", { tool: name, raw });
            }
            return raw;
          }
        }
      }

      logGraphQLDiagnostics("Tool result missing expected content payload", { tool: name, result });
      return result;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("Unknown MCP tool error");
      if (attempt >= maxRetries) {
        break;
      }
      await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
      attempt += 1;
    }
  }
  throw lastError || new Error("MCP call failed");
}

async function parseSSEResponse(response: Response): Promise<unknown> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let lastResult: unknown = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (!data) continue;

      try {
        const parsed = JSON.parse(data);
        if (parsed.result) {
          const content = parsed.result.content;
          if (content) {
            const textItems = content.filter(
              (c: { type: string; text?: string }) => c.type === "text" && c.text
            );
            if (textItems.length > 1) {
              lastResult = textItems.map((item: { text: string }) => {
                try { return JSON.parse(item.text); } catch { return item.text; }
              });
            } else if (textItems.length === 1) {
              try {
                lastResult = JSON.parse(textItems[0].text);
              } catch {
                lastResult = textItems[0].text;
              }
            }
          }
        }
      } catch {
        // Skip malformed data
      }
    }
  }

  return lastResult;
}

/**
 * List available tools from the MCP server.
 */
export async function listMCPTools(): Promise<
  Array<{ name: string; description: string; inputSchema: unknown }>
> {
  const response = await fetch(`${MCP_SERVER_URL}/mcp`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: crypto.randomUUID(),
      method: "tools/list",
      params: {},
    }),
  });

  if (!response.ok) {
    throw new Error(`MCP server error: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  let data: { result?: { tools: Array<{ name: string; description: string; inputSchema: unknown }> } };

  if (contentType.includes("text/event-stream")) {
    const result = await parseSSEResponse(response);
    return (result as { tools: Array<{ name: string; description: string; inputSchema: unknown }> })?.tools || [];
  }

  data = await response.json();
  return data.result?.tools || [];
}
