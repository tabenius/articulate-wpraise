/**
 * MCP HTTP client for communicating with the WordPress MCP server.
 *
 * The MCP server runs as a Docker container with streamable-http transport.
 * This client calls tools on the MCP server via JSON-RPC over HTTP.
 */

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

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

/**
 * Call a tool on the MCP server via the streamable-http transport.
 */
export async function callMCPTool(
  name: string,
  args: Record<string, unknown>,
  authHeaders?: Record<string, string>
): Promise<unknown> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };

  // Forward authentication headers if provided
  if (authHeaders) {
    Object.assign(headers, authHeaders);
  }

  const response = await fetch(`${MCP_SERVER_URL}/message`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: crypto.randomUUID(),
      method: "tools/call",
      params: {
        name,
        arguments: args,
      },
    }),
  });

  if (!response.ok) {
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
    throw new Error(`MCP tool error: ${data.error.message}`);
  }

  // Extract the text content from MCP tool result
  const result = data.result;
  if (result?.content) {
    const textContent = result.content.find((c) => c.type === "text");
    if (textContent?.text) {
      try {
        return JSON.parse(textContent.text);
      } catch {
        return textContent.text;
      }
    }
  }

  return result;
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
            const textContent = content.find(
              (c: { type: string }) => c.type === "text"
            );
            if (textContent?.text) {
              try {
                lastResult = JSON.parse(textContent.text);
              } catch {
                lastResult = textContent.text;
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
  const response = await fetch(`${MCP_SERVER_URL}/message`, {
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
