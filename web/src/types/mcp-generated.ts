/**
 * Auto-generated TypeScript types from MCP server tool schemas.
 * DO NOT EDIT MANUALLY - regenerate using `npm run generate-types`
 *
 * Schema version: 1.0.0
 * Generated: 2026-02-20T08:15:48.676Z
 */

/**
 * MCP Schema Version - used to verify client/server compatibility
 */
export const MCP_SCHEMA_VERSION = "1.0.0";

/**
 * Response from get_posts
 * List WordPress posts and pages with optional filtering.
 */
export type GetPostsResponse = Array<{
    id: number;
    title: string;
    slug: string | null;
    status: string;
    type: string;
    date: string;
    modified?: string;
    excerpt?: string;
    author?: string;
    featuredImage?: {
    id?: number;
    url?: string;
    altText?: string;
    width?: number | null;
    height?: number | null;
  };
  }>;

/**
 * Response from get_post
 * Get a single WordPress post by its database ID.
 */
export type GetPostResponse = {
    id: number;
    title: string;
    slug: string | null;
    status: string;
    content?: string | null;
    date?: string;
    modified?: string;
    author?: string;
    featuredImage?: {
    id?: number;
    url?: string;
    altText?: string;
    width?: number | null;
    height?: number | null;
  };
    categories?: Array<{
    id?: number;
    name?: string;
    slug?: string;
  }>;
    tags?: Array<{
    id?: number;
    name?: string;
    slug?: string;
  }>;
  };

/**
 * Response from create_post
 * Create a new WordPress post or page.
 */
export type CreatePostResponse = {
    id: number;
    title: string;
    slug: string | null;
    status: string;
    content?: string | null;
    date?: string;
    modified?: string;
    author?: string;
  };

/**
 * Response from update_post
 * Update an existing WordPress post.
 */
export type UpdatePostResponse = {
    id: number;
    title: string;
    slug: string | null;
    status: string;
    content?: string | null;
    date?: string;
    modified?: string;
    author?: string;
  };

/**
 * Response from delete_post
 * Delete a WordPress post by its database ID.
 */
export type DeletePostResponse = {
    deleted: boolean;
    id?: number | null;
    title?: string | null;
  };

/**
 * Response from get_blocks
 * Get the structured block tree for a WordPress post.
 */
export type GetBlocksResponse = Record<string, unknown>;

/**
 * Response from update_blocks
 * Update all blocks for a WordPress post.
 */
export type UpdateBlocksResponse = Record<string, unknown>;

/**
 * Response from insert_block
 * Insert a single block into a post at a given position.
 */
export type InsertBlockResponse = Record<string, unknown>;

/**
 * Response from remove_block
 * Remove a block from a post by its clientId.
 */
export type RemoveBlockResponse = Record<string, unknown>;

/**
 * Response from move_block
 * Move a block to a new position within the post.
 */
export type MoveBlockResponse = Record<string, unknown>;

/**
 * Response from get_media
 * List media items from the WordPress media library.
 */
export type GetMediaResponse = Record<string, unknown>;

/**
 * Response from get_media_item
 * Get a single media item with URL, alt text, and dimensions.
 */
export type GetMediaItemResponse = Record<string, unknown>;

/**
 * Response from upload_media
 * Upload a media file to WordPress from a URL or data URI.
 */
export type UploadMediaResponse = Record<string, unknown>;

/**
 * Response from get_categories
 * List WordPress categories.
 */
export type GetCategoriesResponse = Record<string, unknown>;

/**
 * Response from get_tags
 * List WordPress tags.
 */
export type GetTagsResponse = Record<string, unknown>;

/**
 * Response from create_category
 * Create a new WordPress category.
 */
export type CreateCategoryResponse = Record<string, unknown>;

/**
 * Response from create_tag
 * Create a new WordPress tag.
 */
export type CreateTagResponse = Record<string, unknown>;

/**
 * Response from list_menus
 * List all WordPress menus.
 */
export type ListMenusResponse = Record<string, unknown>;

/**
 * Response from get_menu_items
 * Get items in a specific menu.
 */
export type GetMenuItemsResponse = Record<string, unknown>;

/**
 * Response from add_page_to_menu
 * Add a page to a WordPress menu.
 */
export type AddPageToMenuResponse = Record<string, unknown>;

/**
 * Response from remove_page_from_menu
 * Remove a page from a WordPress menu.
 */
export type RemovePageFromMenuResponse = Record<string, unknown>;

/**
 * Response from get_front_page_settings
 * Get current front page settings.
 */
export type GetFrontPageSettingsResponse = Record<string, unknown>;

/**
 * Response from set_front_page
 * Set a page as the site's front page.
 */
export type SetFrontPageResponse = Record<string, unknown>;

/**
 * Response from unset_front_page
 * Unset the front page (show posts on front page instead).
 */
export type UnsetFrontPageResponse = Record<string, unknown>;

/**
 * All available MCP tool names
 */
export type MCPToolName = "get_posts" | "get_post" | "create_post" | "update_post" | "delete_post" | "get_blocks" | "update_blocks" | "insert_block" | "remove_block" | "move_block" | "get_media" | "get_media_item" | "upload_media" | "get_categories" | "get_tags" | "create_category" | "create_tag" | "list_menus" | "get_menu_items" | "add_page_to_menu" | "remove_page_from_menu" | "get_front_page_settings" | "set_front_page" | "unset_front_page";

/**
 * Helper type to get the response type for a specific tool
 */
export type MCPToolResponse<T extends MCPToolName> = 
  T extends "get_posts" ? GetPostsResponse :
  T extends "get_post" ? GetPostResponse :
  T extends "create_post" ? CreatePostResponse :
  T extends "update_post" ? UpdatePostResponse :
  T extends "delete_post" ? DeletePostResponse :
  T extends "get_blocks" ? GetBlocksResponse :
  T extends "update_blocks" ? UpdateBlocksResponse :
  T extends "insert_block" ? InsertBlockResponse :
  T extends "remove_block" ? RemoveBlockResponse :
  T extends "move_block" ? MoveBlockResponse :
  T extends "get_media" ? GetMediaResponse :
  T extends "get_media_item" ? GetMediaItemResponse :
  T extends "upload_media" ? UploadMediaResponse :
  T extends "get_categories" ? GetCategoriesResponse :
  T extends "get_tags" ? GetTagsResponse :
  T extends "create_category" ? CreateCategoryResponse :
  T extends "create_tag" ? CreateTagResponse :
  T extends "list_menus" ? ListMenusResponse :
  T extends "get_menu_items" ? GetMenuItemsResponse :
  T extends "add_page_to_menu" ? AddPageToMenuResponse :
  T extends "remove_page_from_menu" ? RemovePageFromMenuResponse :
  T extends "get_front_page_settings" ? GetFrontPageSettingsResponse :
  T extends "set_front_page" ? SetFrontPageResponse :
  T extends "unset_front_page" ? UnsetFrontPageResponse :
  never;
