<?php
/**
 * Plugin Name: Articulate SSO
 * Description: One-time token login for Articulate platform users.
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Handle SSO login via one-time token.
 * URL: /wp-login.php?articulate_token=<token>
 */
add_action('login_init', function () {
    if (empty($_GET['articulate_token'])) {
        return;
    }

    $token = sanitize_text_field($_GET['articulate_token']);

    // Validate token with MCP server via control_net
    $mcp_url = getenv('ARTICULATE_MCP_URL') ?: 'http://articulate-mcp:8000';
    $response = wp_remote_post($mcp_url . '/auth/validate-wp-login-token', [
        'headers' => ['Content-Type' => 'application/json'],
        'body'    => wp_json_encode(['token' => $token]),
        'timeout' => 10,
    ]);

    if (is_wp_error($response)) {
        wp_die('SSO authentication failed: unable to reach authentication server.', 'Login Error', ['response' => 502]);
    }

    $status = wp_remote_retrieve_response_code($response);
    $body   = json_decode(wp_remote_retrieve_body($response), true);

    if ($status !== 200 || empty($body['valid'])) {
        wp_die('Invalid or expired login token.', 'Login Error', ['response' => 403]);
    }

    // Get or create the admin user for this tenant
    $user = get_user_by('login', 'articulate-admin');
    if (!$user) {
        $user_id = wp_insert_user([
            'user_login' => 'articulate-admin',
            'user_pass'  => wp_generate_password(32),
            'user_email' => 'admin@articulate.local',
            'role'       => 'administrator',
            'display_name' => 'Articulate Admin',
        ]);
        if (is_wp_error($user_id)) {
            wp_die('Failed to create admin user.', 'Login Error', ['response' => 500]);
        }
        $user = get_user_by('ID', $user_id);
    }

    // Log in
    wp_set_current_user($user->ID);
    wp_set_auth_cookie($user->ID, false);
    do_action('wp_login', $user->user_login, $user);

    // Redirect to wp-admin
    wp_safe_redirect(admin_url());
    exit;
});
