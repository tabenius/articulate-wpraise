/**
 * Claude API client for the server-side chat route.
 *
 * Uses the Anthropic SDK for streaming completions with tool use.
 */

import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-sonnet-4-5-20250514";

export function createAnthropicClient(apiKey?: string): Anthropic {
  return new Anthropic({
    apiKey: apiKey || process.env.ANTHROPIC_API_KEY,
  });
}

export function getSystemPrompt(postContext?: {
  id: number;
  title: string;
  blockCount: number;
}): string {
  let prompt = `You are Articulate, an intelligent WordPress content editor assistant. You help users create, edit, and manage WordPress content through conversation.

You have access to tools that interact with a WordPress site via the MCP (Model Context Protocol) server. You can:
- Create, read, update, and delete posts and pages
- View, insert, remove, move, and update individual blocks within posts
- Search content across the site
- Access the media library

When the user asks you to modify content, use the appropriate tools. Always confirm what you've done after making changes.

WordPress Block Types you can use:
- core/paragraph: Text paragraph. Attributes: {content: "text", align: "left|center|right"}
- core/heading: Heading h1-h6. Attributes: {content: "text", level: 1-6}
- core/image: Image. Attributes: {url: "image_url", alt: "alt text", caption: "caption"}
- core/list: Bulleted or numbered list. Attributes: {ordered: true|false, values: "<li>item</li>"}
- core/quote: Blockquote. Attributes: {value: "<p>quote text</p>", citation: "author"}
- core/code: Code block. Attributes: {content: "code here"}
- core/columns: Multi-column layout (contains core/column inner blocks)
- core/group: Container for grouping blocks
- core/buttons: Button group (contains core/button inner blocks)
- core/button: Button. Attributes: {text: "Click me", url: "https://..."}
- core/spacer: Vertical space. Attributes: {height: "50px"}
- core/separator: Horizontal divider line

Guidelines:
- When adding content, prefer structured blocks over raw HTML
- Keep responses concise and focused on the action taken
- If the user's request is ambiguous, ask for clarification
- After modifying blocks, briefly describe what was changed`;

  if (postContext) {
    prompt += `\n\nCurrently editing post #${postContext.id}: "${postContext.title}" (${postContext.blockCount} blocks)`;
  }

  return prompt;
}

/**
 * Define MCP tools in Claude API tool format.
 */
export function getToolDefinitions(): Anthropic.Messages.Tool[] {
  return [
    {
      name: "get_posts",
      description:
        "List WordPress posts with optional filtering by status and search term.",
      input_schema: {
        type: "object" as const,
        properties: {
          status: {
            type: "string",
            description: "Post status filter (publish, draft, pending, private)",
            default: "publish",
          },
          per_page: {
            type: "number",
            description: "Number of posts to return (max 100)",
            default: 10,
          },
          search: {
            type: "string",
            description: "Search term to filter by title/content",
          },
        },
      },
    },
    {
      name: "get_post",
      description: "Get a single WordPress post by its database ID, including content.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
        },
        required: ["post_id"],
      },
    },
    {
      name: "create_post",
      description: "Create a new WordPress post with a title and optional content.",
      input_schema: {
        type: "object" as const,
        properties: {
          title: { type: "string", description: "The post title" },
          content: {
            type: "string",
            description: "Post content in WordPress block format",
          },
          status: {
            type: "string",
            description: "Post status (draft, publish)",
            default: "draft",
          },
        },
        required: ["title"],
      },
    },
    {
      name: "update_post",
      description: "Update an existing WordPress post's title, content, or status.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
          title: { type: "string", description: "New title" },
          content: { type: "string", description: "New content" },
          status: { type: "string", description: "New status" },
        },
        required: ["post_id"],
      },
    },
    {
      name: "delete_post",
      description: "Delete a WordPress post by its database ID.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
        },
        required: ["post_id"],
      },
    },
    {
      name: "get_blocks",
      description:
        "Get the structured block tree for a WordPress post. Returns blocks with name, clientId, attributes, innerBlocks.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
        },
        required: ["post_id"],
      },
    },
    {
      name: "update_blocks",
      description:
        "Replace all blocks in a WordPress post. Each block needs: name (string), attributes (object), optionally innerBlocks (array).",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
          blocks: {
            type: "array",
            description: "Array of block objects",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                attributes: { type: "object" },
                innerBlocks: { type: "array" },
              },
              required: ["name", "attributes"],
            },
          },
        },
        required: ["post_id", "blocks"],
      },
    },
    {
      name: "insert_block",
      description:
        'Insert a single block into a post at a given position. Example block: {"name": "core/paragraph", "attributes": {"content": "Hello"}}',
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
          block: {
            type: "object",
            description: "Block to insert",
            properties: {
              name: { type: "string" },
              attributes: { type: "object" },
              innerBlocks: { type: "array" },
            },
            required: ["name", "attributes"],
          },
          position: {
            type: "number",
            description: "Position (0-indexed). -1 = append to end",
            default: -1,
          },
        },
        required: ["post_id", "block"],
      },
    },
    {
      name: "remove_block",
      description: "Remove a block from a post by its clientId.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
          client_id: {
            type: "string",
            description: "The clientId of the block to remove",
          },
        },
        required: ["post_id", "client_id"],
      },
    },
    {
      name: "move_block",
      description: "Move a block to a new position within the post.",
      input_schema: {
        type: "object" as const,
        properties: {
          post_id: { type: "number", description: "The post database ID" },
          client_id: { type: "string", description: "The block clientId" },
          new_position: {
            type: "number",
            description: "Target position (0-indexed)",
          },
        },
        required: ["post_id", "client_id", "new_position"],
      },
    },
    {
      name: "search_content",
      description: "Search WordPress posts and pages by keyword.",
      input_schema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Search term" },
          content_type: {
            type: "string",
            description: "post, page, or all",
            default: "all",
          },
          per_page: { type: "number", default: 10 },
        },
        required: ["query"],
      },
    },
    {
      name: "get_pages",
      description: "List WordPress pages.",
      input_schema: {
        type: "object" as const,
        properties: {
          per_page: { type: "number", default: 10 },
        },
      },
    },
    {
      name: "get_media",
      description: "List media items from the WordPress media library.",
      input_schema: {
        type: "object" as const,
        properties: {
          per_page: { type: "number", default: 10 },
        },
      },
    },
  ];
}

export { MODEL };
