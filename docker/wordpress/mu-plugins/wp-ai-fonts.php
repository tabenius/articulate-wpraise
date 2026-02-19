<?php
/**
 * Plugin Name: WP-AI Font Manager
 * Description: Manages font uploads and automatic @font-face registration
 * Version: 1.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class WP_AI_Font_Manager {
    const OPTION_KEY = 'wp_ai_registered_fonts';
    const API_NAMESPACE = 'wp-ai/v1';
    const UPLOAD_DIR = 'fonts';

    public function __construct() {
        add_action('rest_api_init', [$this, 'register_routes']);
        add_action('wp_head', [$this, 'inject_font_css']);
        add_action('admin_head', [$this, 'inject_font_css']);
    }

    /**
     * Register REST API routes
     */
    public function register_routes() {
        register_rest_route(self::API_NAMESPACE, '/fonts/upload', [
            'methods' => 'POST',
            'callback' => [$this, 'handle_font_upload'],
            'permission_callback' => [$this, 'check_permission'],
        ]);

        register_rest_route(self::API_NAMESPACE, '/fonts', [
            'methods' => 'GET',
            'callback' => [$this, 'list_fonts'],
            'permission_callback' => [$this, 'check_permission'],
        ]);

        register_rest_route(self::API_NAMESPACE, '/fonts/(?P<id>[a-zA-Z0-9_-]+)', [
            'methods' => 'DELETE',
            'callback' => [$this, 'delete_font'],
            'permission_callback' => [$this, 'check_permission'],
        ]);
    }

    /**
     * Check if user has permission to manage fonts
     */
    public function check_permission() {
        return current_user_can('upload_files');
    }

    /**
     * Handle font upload
     */
    public function handle_font_upload($request) {
        $files = $request->get_file_params();

        if (empty($files['file'])) {
            return new WP_Error('no_file', 'No file uploaded', ['status' => 400]);
        }

        $file = $files['file'];
        $font_family = $request->get_param('font_family');
        $font_weight = $request->get_param('font_weight') ?: '400';
        $font_style = $request->get_param('font_style') ?: 'normal';

        // Validate file type
        $allowed_types = ['woff2', 'woff', 'ttf', 'otf', 'eot'];
        $file_ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));

        if (!in_array($file_ext, $allowed_types)) {
            return new WP_Error('invalid_type', 'Invalid font file type', ['status' => 400]);
        }

        // Extract font family from filename if not provided
        if (empty($font_family)) {
            $font_family = $this->extract_font_family($file['name']);
        }

        // Sanitize font family for use in directory name
        $font_family_slug = sanitize_title($font_family);

        // Create upload directory
        $upload_dir = wp_upload_dir();
        $font_dir = $upload_dir['basedir'] . '/' . self::UPLOAD_DIR . '/' . $font_family_slug;

        if (!file_exists($font_dir)) {
            wp_mkdir_p($font_dir);
        }

        // Generate unique filename
        $filename = sanitize_file_name($file['name']);
        $filepath = $font_dir . '/' . $filename;

        // Handle file upload
        if (!move_uploaded_file($file['tmp_name'], $filepath)) {
            return new WP_Error('upload_failed', 'Failed to upload file', ['status' => 500]);
        }

        // Generate font URL
        $font_url = $upload_dir['baseurl'] . '/' . self::UPLOAD_DIR . '/' . $font_family_slug . '/' . $filename;

        // Generate unique ID for this font variant
        $font_id = $font_family_slug . '-' . $font_weight . '-' . $font_style;

        // Generate @font-face CSS
        $css = $this->generate_font_face_css($font_family, $font_weight, $font_style, $font_url, $file_ext);

        // Store font metadata
        $fonts = get_option(self::OPTION_KEY, []);
        $fonts[$font_id] = [
            'id' => $font_id,
            'family' => $font_family,
            'weight' => $font_weight,
            'style' => $font_style,
            'url' => $font_url,
            'format' => $file_ext,
            'css' => $css,
            'uploaded_at' => current_time('mysql'),
        ];
        update_option(self::OPTION_KEY, $fonts);

        return rest_ensure_response([
            'success' => true,
            'font' => $fonts[$font_id],
        ]);
    }

    /**
     * List all registered fonts
     */
    public function list_fonts() {
        $fonts = get_option(self::OPTION_KEY, []);
        return rest_ensure_response([
            'success' => true,
            'fonts' => array_values($fonts),
        ]);
    }

    /**
     * Delete a font
     */
    public function delete_font($request) {
        $font_id = $request->get_param('id');
        $fonts = get_option(self::OPTION_KEY, []);

        if (!isset($fonts[$font_id])) {
            return new WP_Error('not_found', 'Font not found', ['status' => 404]);
        }

        // Delete the font file
        $font_data = $fonts[$font_id];
        $upload_dir = wp_upload_dir();
        $file_path = str_replace($upload_dir['baseurl'], $upload_dir['basedir'], $font_data['url']);

        if (file_exists($file_path)) {
            unlink($file_path);
        }

        // Remove from registry
        unset($fonts[$font_id]);
        update_option(self::OPTION_KEY, $fonts);

        return rest_ensure_response([
            'success' => true,
            'message' => 'Font deleted successfully',
        ]);
    }

    /**
     * Extract font family name from filename
     */
    private function extract_font_family($filename) {
        $name = pathinfo($filename, PATHINFO_FILENAME);
        // Remove common suffixes
        $name = preg_replace('/-?(regular|bold|italic|light|medium|semibold|thin|black|oblique)$/i', '', $name);
        // Remove weight indicators
        $name = preg_replace('/-?(100|200|300|400|500|600|700|800|900)$/i', '', $name);
        // Convert to title case
        return ucwords(str_replace(['-', '_'], ' ', $name));
    }

    /**
     * Generate @font-face CSS
     */
    private function generate_font_face_css($family, $weight, $style, $url, $format) {
        // Map file extensions to CSS format values
        $format_map = [
            'woff2' => 'woff2',
            'woff' => 'woff',
            'ttf' => 'truetype',
            'otf' => 'opentype',
            'eot' => 'embedded-opentype',
        ];

        $css_format = $format_map[$format] ?? $format;

        $css = "@font-face {\n";
        $css .= "    font-family: '{$family}';\n";
        $css .= "    src: url('{$url}') format('{$css_format}');\n";
        $css .= "    font-weight: {$weight};\n";
        $css .= "    font-style: {$style};\n";
        $css .= "    font-display: swap;\n";
        $css .= "}";

        return $css;
    }

    /**
     * Inject font CSS into page head
     */
    public function inject_font_css() {
        $fonts = get_option(self::OPTION_KEY, []);

        if (empty($fonts)) {
            return;
        }

        echo "<style id='wp-ai-fonts'>\n";
        foreach ($fonts as $font) {
            echo $font['css'] . "\n";
        }
        echo "</style>\n";
    }
}

// Initialize the plugin
new WP_AI_Font_Manager();
