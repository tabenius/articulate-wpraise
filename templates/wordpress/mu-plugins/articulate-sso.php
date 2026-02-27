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

    // Use per-user WordPress account if available, fallback to shared admin
    $wp_username = !empty($body['wp_username']) ? sanitize_user($body['wp_username']) : 'articulate-admin';
    $wp_role = !empty($body['wp_role']) ? sanitize_text_field($body['wp_role']) : 'administrator';
    $wp_email = !empty($body['email']) ? sanitize_email($body['email']) : 'admin@articulate.local';
    $wp_name = !empty($body['name']) ? sanitize_text_field($body['name']) : 'Articulate Admin';

    $user = get_user_by('login', $wp_username);
    if (!$user) {
        $user_id = wp_insert_user([
            'user_login'   => $wp_username,
            'user_pass'    => wp_generate_password(32),
            'user_email'   => $wp_email,
            'role'         => $wp_role,
            'display_name' => $wp_name,
        ]);
        if (is_wp_error($user_id)) {
            wp_die('Failed to create user account.', 'Login Error', ['response' => 500]);
        }
        $user = get_user_by('ID', $user_id);
    } else {
        // Update role if it changed
        if (!in_array($wp_role, $user->roles)) {
            $user->set_role($wp_role);
        }
    }

    // Log in
    wp_set_current_user($user->ID);
    wp_set_auth_cookie($user->ID, false);
    do_action('wp_login', $user->user_login, $user);

    // Redirect to wp-admin
    wp_safe_redirect(admin_url());
    exit;
});
