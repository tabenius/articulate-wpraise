# WordPress SEO Meta Fields Implementation

## Overview
Implementation of comprehensive SEO meta fields for WordPress posts and pages, compatible with Yoast SEO and RankMath standards.

## Field Categories

### 1. General SEO Meta
| Field | Meta Key | Description | Character Limit |
|-------|----------|-------------|-----------------|
| SEO Title | `_wp_ai_seo_title` | Page title for search engines | 60 chars recommended |
| Meta Description | `_wp_ai_seo_description` | Description for search snippets | 155-160 chars recommended |
| Focus Keyword | `_wp_ai_seo_focus_keyword` | Primary keyword for page | N/A |
| Canonical URL | `_wp_ai_seo_canonical` | Canonical URL to prevent duplicates | Valid URL |
| Meta Robots | `_wp_ai_seo_robots` | Index/follow directives | JSON array |

### 2. Open Graph (Facebook, LinkedIn)
| Field | Meta Key | Description |
|-------|----------|-------------|
| OG Title | `_wp_ai_og_title` | Social media title |
| OG Description | `_wp_ai_og_description` | Social media description |
| OG Image | `_wp_ai_og_image` | Social media image URL |
| OG Type | `_wp_ai_og_type` | Content type (article, website, etc.) |

### 3. Twitter Cards
| Field | Meta Key | Description |
|-------|----------|-------------|
| Twitter Card Type | `_wp_ai_twitter_card` | Card type (summary, summary_large_image) |
| Twitter Title | `_wp_ai_twitter_title` | Twitter-specific title |
| Twitter Description | `_wp_ai_twitter_description` | Twitter-specific description |
| Twitter Image | `_wp_ai_twitter_image` | Twitter card image URL |

### 4. Advanced SEO
| Field | Meta Key | Description |
|-------|----------|-------------|
| Breadcrumb Title | `_wp_ai_seo_breadcrumb_title` | Custom breadcrumb text |
| Schema Type | `_wp_ai_schema_type` | Schema.org type |

## Storage Method
All fields stored as WordPress post meta (custom fields) using the `wp_postmeta` table:
- `post_id`: References wp_posts
- `meta_key`: Field identifier (e.g., `_wp_ai_seo_title`)
- `meta_value`: Field value

## Meta Robots Options
- `noindex`: Don't index this page
- `nofollow`: Don't follow links on this page
- `noarchive`: Don't show cached version
- `nosnippet`: Don't show snippet in search results
- `noimageindex`: Don't index images

## Default Fallback Behavior
If SEO fields are not set, fallback to:
- SEO Title → Post title
- Meta Description → Post excerpt or first 155 chars
- OG Title → SEO Title → Post title
- OG Description → Meta Description → Post excerpt
- Twitter Title → OG Title → SEO Title → Post title
- Twitter Description → OG Description → Meta Description

## Character Count Guidelines
- **SEO Title**: 50-60 characters (Google displays ~60)
- **Meta Description**: 150-160 characters (Google displays ~155-160)
- **OG Title**: 60-90 characters (Facebook truncates at ~95)
- **OG Description**: 200 characters (Facebook truncates at ~200)
- **Twitter Title**: 70 characters
- **Twitter Description**: 200 characters

## Implementation Notes
- Prefix all meta keys with `_wp_ai_` to namespace them
- Use underscore prefix `_` to hide from WordPress custom fields UI
- Store robots directives as JSON array for flexibility
- Validate URLs for canonical and image fields
- Provide real-time character counters in UI
- Show preview snippets for Google/Facebook/Twitter
