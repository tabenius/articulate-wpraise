/**
 * WordPress Block Serializer/Parser
 * Converts between WordPress block comments and Block[] structure
 */

import type { Block } from "@/types/blocks";

/**
 * Parse WordPress block comment format to Block[] structure
 */
export function parseBlocks(content: string): Block[] {
  if (!content || typeof content !== "string") {
    return [];
  }

  const blocks: Block[] = [];
  const blockRegex = /<!--\s+wp:(\S+)(\s+(\{[^}]*\}))?\s+-->([\s\S]*?)<!--\s+\/wp:\1\s+-->/g;

  let match;
  let lastIndex = 0;

  while ((match = blockRegex.exec(content)) !== null) {
    const [fullMatch, blockName, , attributesJson, innerContent] = match;

    // Parse attributes if present
    let attributes: Record<string, unknown> = {};
    if (attributesJson) {
      try {
        attributes = JSON.parse(attributesJson.trim());
      } catch (error) {
        console.warn(`Failed to parse block attributes for ${blockName}:`, error);
      }
    }

    // Extract inner HTML content (strip the block wrapper)
    const innerHTML = innerContent?.trim() || "";

    // Parse inner blocks recursively
    const innerBlocks = innerHTML.includes("<!-- wp:")
      ? parseBlocks(innerHTML)
      : [];

    // Extract text content from HTML for certain block types
    if (blockName === "paragraph" && innerHTML) {
      attributes.content = innerHTML;
    } else if (blockName === "heading" && innerHTML) {
      attributes.content = innerHTML;
      // Try to extract heading level from HTML tag
      const headingMatch = innerHTML.match(/<h(\d)>/);
      if (headingMatch && !attributes.level) {
        attributes.level = parseInt(headingMatch[1], 10);
      }
    } else if (blockName === "list" && innerHTML) {
      attributes.values = innerHTML;
      // Detect if ordered or unordered
      if (innerHTML.startsWith("<ol>")) {
        attributes.ordered = true;
      } else if (innerHTML.startsWith("<ul>")) {
        attributes.ordered = false;
      }
    } else if (blockName === "quote" && innerHTML) {
      attributes.value = innerHTML;
    } else if (blockName === "code" && innerHTML) {
      attributes.content = innerHTML.replace(/<\/?code>/g, "");
    } else if (blockName === "image" && innerHTML) {
      // Extract image attributes from HTML
      const imgMatch = innerHTML.match(/<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>/);
      if (imgMatch) {
        attributes.url = imgMatch[1];
        attributes.alt = imgMatch[2];
      }
    }

    blocks.push({
      clientId: `block-${Date.now()}-${Math.random()}`,
      name: `core/${blockName}`,
      attributes,
      innerBlocks,
    });

    lastIndex = match.index + fullMatch.length;
  }

  // Handle self-closing blocks (like separator, spacer)
  const selfClosingRegex = /<!--\s+wp:(\S+)(\s+(\{[^}]*\}))?\s+\/-->/g;

  while ((match = selfClosingRegex.exec(content)) !== null) {
    const [, blockName, , attributesJson] = match;

    let attributes: Record<string, unknown> = {};
    if (attributesJson) {
      try {
        attributes = JSON.parse(attributesJson.trim());
      } catch (error) {
        console.warn(`Failed to parse block attributes for ${blockName}:`, error);
      }
    }

    blocks.push({
      clientId: `block-${Date.now()}-${Math.random()}`,
      name: `core/${blockName}`,
      attributes,
      innerBlocks: [],
    });
  }

  return blocks;
}

/**
 * Serialize Block[] structure to WordPress block comment format
 */
export function serializeBlocks(blocks: Block[]): string {
  if (!Array.isArray(blocks)) {
    return "";
  }

  return blocks.map((block) => serializeBlock(block)).join("\n\n");
}

/**
 * Serialize a single block to WordPress format
 */
function serializeBlock(block: Block): string {
  if (!block || !block.name) {
    return "";
  }

  // Extract block type from name (remove "core/" prefix)
  const blockType = block.name.replace("core/", "");

  // Filter out internal attributes (clientId, etc.)
  const attributes = { ...block.attributes };
  const content = attributes.content as string | undefined;
  const value = attributes.value as string | undefined;
  const values = attributes.values as string | undefined;

  // Build attributes JSON (exclude content fields)
  const attrObj: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(attributes)) {
    if (key !== "content" && key !== "value" && key !== "values") {
      attrObj[key] = val;
    }
  }

  const hasAttributes = Object.keys(attrObj).length > 0;
  const attrString = hasAttributes ? ` ${JSON.stringify(attrObj)}` : "";

  // Handle self-closing blocks
  if (
    blockType === "separator" ||
    blockType === "spacer" ||
    (blockType === "image" && !content && !value)
  ) {
    return `<!-- wp:${blockType}${attrString} /-->`;
  }

  // Generate inner HTML based on block type
  let innerHtml = "";

  if (blockType === "paragraph" && content) {
    innerHtml = content;
  } else if (blockType === "heading" && content) {
    const level = (attributes.level as number) || 2;
    innerHtml = `<h${level}>${content}</h${level}>`;
  } else if (blockType === "list" && values) {
    const ordered = attributes.ordered as boolean;
    const tag = ordered ? "ol" : "ul";
    innerHtml = `<${tag}>${values}</${tag}>`;
  } else if (blockType === "quote" && value) {
    innerHtml = value;
  } else if (blockType === "code" && content) {
    innerHtml = `<code>${content}</code>`;
  } else if (blockType === "image" && attributes.url) {
    const { url, alt = "" } = attributes as { url: string; alt?: string };
    innerHtml = `<figure class="wp-block-image"><img src="${url}" alt="${alt}"/></figure>`;
  } else if (blockType === "columns" || blockType === "group") {
    // Handle container blocks with inner blocks
    innerHtml = block.innerBlocks.map(serializeBlock).join("\n");
  } else {
    // Fallback: use content if available
    innerHtml = (content || value || values || "") as string;
  }

  // Serialize inner blocks if present
  if (block.innerBlocks.length > 0 && !innerHtml) {
    innerHtml = block.innerBlocks.map(serializeBlock).join("\n");
  }

  return `<!-- wp:${blockType}${attrString} -->\n${innerHtml}\n<!-- /wp:${blockType} -->`;
}

/**
 * Convert raw HTML to a single HTML block (fallback)
 */
export function htmlToBlock(html: string): Block {
  return {
    clientId: `block-${Date.now()}-${Math.random()}`,
    name: "core/html",
    attributes: {
      content: html || "",
    },
    innerBlocks: [],
  };
}
