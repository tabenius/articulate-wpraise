import { NextRequest } from "next/server";
import {
  createAnthropicClient,
  getSystemPrompt,
  getToolDefinitions,
  MODEL,
} from "@/lib/claude";
import { callMCPTool } from "@/lib/mcp-client";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { messages, postId } = body;

    // Use BYOK key from header, or fall back to server env
    const clientKey = request.headers.get("X-API-Key");
    const apiKey = clientKey || process.env.ANTHROPIC_API_KEY;

    if (!apiKey) {
      return new Response(
        JSON.stringify({
          error:
            "No API key configured. Set ANTHROPIC_API_KEY in .env.local or provide your key in Settings.",
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    }

    const anthropic = createAnthropicClient(apiKey);

    // Build system prompt with post context
    let postContext: { id: number; title: string; blockCount: number } | undefined;
    if (postId) {
      try {
        const post = (await callMCPTool("get_post", {
          post_id: postId,
        })) as { id: number; title: string };
        const blocks = (await callMCPTool("get_blocks", {
          post_id: postId,
        })) as unknown[];
        postContext = {
          id: postId,
          title: post?.title || "Untitled",
          blockCount: Array.isArray(blocks) ? blocks.length : 0,
        };
      } catch {
        // Continue without post context
      }
    }

    const systemPrompt = getSystemPrompt(postContext);
    const tools = getToolDefinitions();

    // Create SSE stream
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const send = (event: Record<string, unknown>) => {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
          );
        };

        try {
          // Agentic loop: keep going while Claude wants to use tools
          let currentMessages = [...messages];
          let iterations = 0;
          const MAX_ITERATIONS = 10;

          while (iterations < MAX_ITERATIONS) {
            iterations++;

            const response = await anthropic.messages.create({
              model: MODEL,
              max_tokens: 4096,
              system: systemPrompt,
              messages: currentMessages,
              tools,
            });

            // Process response content blocks
            let hasToolUse = false;
            const toolResults: Array<{
              type: "tool_result";
              tool_use_id: string;
              content: string;
            }> = [];

            for (const block of response.content) {
              if (block.type === "text") {
                send({ type: "text", content: block.text });
              } else if (block.type === "tool_use") {
                hasToolUse = true;
                const toolCallId = block.id;

                send({
                  type: "tool_use",
                  id: toolCallId,
                  name: block.name,
                  input: block.input,
                });

                // Execute the tool via MCP
                try {
                  const result = await callMCPTool(
                    block.name,
                    block.input as Record<string, unknown>
                  );
                  const resultStr =
                    typeof result === "string"
                      ? result
                      : JSON.stringify(result);

                  send({
                    type: "tool_result",
                    id: toolCallId,
                    result,
                  });

                  toolResults.push({
                    type: "tool_result",
                    tool_use_id: toolCallId,
                    content: resultStr,
                  });
                } catch (toolError) {
                  const errMsg =
                    toolError instanceof Error
                      ? toolError.message
                      : "Tool execution failed";

                  send({
                    type: "tool_result",
                    id: toolCallId,
                    result: { error: errMsg },
                    error: true,
                  });

                  toolResults.push({
                    type: "tool_result",
                    tool_use_id: toolCallId,
                    content: JSON.stringify({ error: errMsg }),
                  });
                }
              }
            }

            // If Claude used tools, continue the conversation with results
            if (hasToolUse && toolResults.length > 0) {
              currentMessages = [
                ...currentMessages,
                { role: "assistant" as const, content: response.content },
                { role: "user" as const, content: toolResults },
              ];
              // Continue the loop - Claude may want to use more tools or respond
            } else {
              // No tool use - we're done
              break;
            }

            // Check stop reason
            if (response.stop_reason === "end_turn") {
              break;
            }
          }
        } catch (error) {
          const errMsg =
            error instanceof Error ? error.message : "Unknown error";
          send({ type: "error", content: errMsg });
        }

        send({ type: "done" });
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
