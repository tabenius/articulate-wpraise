<?php
/**
 * Plugin Name: WP-AI Preview Renderer
 * Description: Provides REST endpoint for live post preview with theme rendering
 * Version: 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class WP_AI_Preview_Renderer {
    public function __construct() {
        add_action('rest_api_init', [$this, 'register_routes']);
    }

    /**
     * Register REST API routes
     */
    public function register_routes() {
        register_rest_route('wp-ai/v1', '/preview/(?P<id>\d+)', [
            'methods' => 'GET',
            'callback' => [$this, 'render_preview'],
            'permission_callback' => [$this, 'check_permission'],
            'args' => [
                'id' => [
                    'required' => true,
                    'validate_callback' => function($param) {
                        return is_numeric($param);
                    }
                ]
            ]
        ]);
    }

    /**
     * Check if user has permission to view previews
     */
    public function check_permission() {
        // Allow authenticated users who can edit posts
        return current_user_can('edit_posts');
    }

    /**
     * Render post preview with active WordPress theme
     */
    public function render_preview($request) {
        $post_id = (int) $request->get_param('id');
        $post = get_post($post_id);

        if (!$post) {
            return new WP_Error('not_found', 'Post not found', ['status' => 404]);
        }

        // Setup post data for theme template tags
        global $wp_query, $post;
        $wp_query->is_singular = true;
        $wp_query->is_single = ($post->post_type === 'post');
        $wp_query->is_page = ($post->post_type === 'page');
        setup_postdata($post);

        // Start output buffering
        ob_start();

        ?>
        <!DOCTYPE html>
        <html <?php language_attributes(); ?>>
        <head>
            <meta charset="<?php bloginfo('charset'); ?>">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="robots" content="noindex, nofollow">
            <?php wp_head(); ?>
            <style>
                /* Prevent admin bar from showing in preview */
                #wpadminbar {
                    display: none !important;
                }
                html {
                    margin-top: 0 !important;
                }
                /* Add subtle preview indicator */
                body::before {
                    content: "Preview Mode";
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: #f0f0f1;
                    color: #2c3338;
                    padding: 8px 16px;
                    text-align: center;
                    font-size: 12px;
                    font-weight: 600;
                    z-index: 999999;
                    border-bottom: 1px solid #dcdcde;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
                }
                body {
                    padding-top: 36px !important;
                }
            </style>
        </head>
        <body <?php body_class(); ?>>
        <?php wp_body_open(); ?>

        <div id="page" class="site">
            <?php
            // Try to use theme's template
            if (function_exists('get_header')) {
                // Remove the doctype/html/head that get_header() outputs
                // We'll just get the header content
                ob_start();
                get_header();
                $header = ob_get_clean();
                // Extract just the header content (skip doctype/html/head)
                if (preg_match('/<body[^>]*>(.*)/is', $header, $matches)) {
                    echo $matches[1];
                }
            }
            ?>

            <main id="main" class="site-main">
                <article id="post-<?php echo $post_id; ?>" <?php post_class(); ?>>
                    <?php if ($post->post_title): ?>
                    <header class="entry-header">
                        <h1 class="entry-title"><?php echo esc_html($post->post_title); ?></h1>
                        <?php if (get_post_meta($post_id, '_thumbnail_id', true)): ?>
                        <div class="post-thumbnail">
                            <?php echo get_the_post_thumbnail($post_id, 'large'); ?>
                        </div>
                        <?php endif; ?>
                    </header>
                    <?php endif; ?>

                    <div class="entry-content">
                        <?php
                        // Apply WordPress content filters (shortcodes, embeds, etc.)
                        echo apply_filters('the_content', $post->post_content);
                        ?>
                    </div>
                </article>
            </main>

            <?php
            if (function_exists('get_footer')) {
                get_footer();
            }
            ?>
        </div>

        <?php wp_footer(); ?>
        </body>
        </html>
        <?php

        $html = ob_get_clean();
        wp_reset_postdata();

        // Return JSON response with HTML
        return [
            'success' => true,
            'html' => $html,
            'post_id' => $post_id,
            'theme' => get_stylesheet(),
            'post_type' => $post->post_type,
            'post_status' => $post->post_status,
        ];
    }
}

// Initialize the plugin
new WP_AI_Preview_Renderer();
