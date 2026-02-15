"""Pytest fixtures for MCP server tests."""

import pytest


@pytest.fixture
def sample_block_content() -> str:
    """Sample WordPress block content for testing."""
    return """<!-- wp:heading {"level":1} -->
<h1 class="wp-block-heading">Hello World</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>This is a test paragraph.</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list">
<li>Item one</li>
<li>Item two</li>
</ul>
<!-- /wp:list -->

<!-- wp:quote -->
<blockquote class="wp-block-quote"><p>A wise quote</p><cite>Author</cite></blockquote>
<!-- /wp:quote -->

<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:paragraph -->
<p>Left column</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:paragraph -->
<p>Right column</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->"""


@pytest.fixture
def sample_blocks() -> list[dict]:
    """Sample block data for testing serialization."""
    return [
        {
            "name": "core/heading",
            "attributes": {"content": "Test Heading", "level": 2},
            "innerBlocks": [],
        },
        {
            "name": "core/paragraph",
            "attributes": {"content": "Test paragraph content."},
            "innerBlocks": [],
        },
        {
            "name": "core/image",
            "attributes": {
                "url": "https://example.com/image.jpg",
                "alt": "Test image",
                "caption": "A test caption",
            },
            "innerBlocks": [],
        },
    ]
