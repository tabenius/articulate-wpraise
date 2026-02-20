<?php
/**
 * Plugin Name: Enable GraphQL Introspection
 * Description: Enables public GraphQL introspection for WP-AI code generation
 * Version: 1.0.0
 */

// Enable GraphQL introspection for public requests
add_filter( 'graphql_introspection_enabled_for_public_requests', '__return_true' );

// Enable GraphQL debug mode
if ( ! defined( 'GRAPHQL_DEBUG' ) ) {
    define( 'GRAPHQL_DEBUG', true );
}
