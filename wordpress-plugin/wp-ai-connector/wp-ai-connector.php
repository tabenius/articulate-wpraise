<?php
/**
 * Plugin Name: Articulate Connector
 * Plugin URI: https://github.com/tabenius/wpraise
 * Description: Automatically register this WordPress site with Articulate platform for AI-powered content management
 * Version: 1.0.0
 * Author: Articulate Team
 * License: GPL-2.0+
 * License URI: http://www.gnu.org/licenses/gpl-2.0.txt
 * Text Domain: wp-ai-connector
 * Requires at least: 5.6
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

class WP_AI_Connector {
    const API_ENDPOINT = 'http://localhost:8000/api/register-wordpress';
    const OPTION_NAME = 'wpai_connector_config';
    const GRAPHQL_PLUGIN = 'wp-graphql/wp-graphql.php';

    private $admin_notices = [];

    public function __construct() {
        register_activation_hook(__FILE__, [$this, 'on_activation']);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_notices', [$this, 'display_admin_notices']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_assets']);
        add_action('wp_ajax_wpai_register_site', [$this, 'ajax_register_site']);
        add_action('wp_ajax_wpai_disconnect_site', [$this, 'ajax_disconnect_site']);
    }

    public function on_activation() {
        // Check WordPress version
        if (version_compare(get_bloginfo('version'), '5.6', '<')) {
            deactivate_plugins(plugin_basename(__FILE__));
            wp_die(
                __('Articulate Connector requires WordPress 5.6 or higher for Application Password support.', 'wp-ai-connector'),
                __('Plugin Activation Error', 'wp-ai-connector'),
                ['back_link' => true]
            );
        }

        // Check PHP version
        if (version_compare(PHP_VERSION, '7.4', '<')) {
            deactivate_plugins(plugin_basename(__FILE__));
            wp_die(
                __('Articulate Connector requires PHP 7.4 or higher.', 'wp-ai-connector'),
                __('Plugin Activation Error', 'wp-ai-connector'),
                ['back_link' => true]
            );
        }

        // Check if WPGraphQL is installed
        if (!$this->is_wpgraphql_installed()) {
            $this->add_notice(
                'warning',
                __('WPGraphQL plugin is required for Articulate Connector. Please install and activate WPGraphQL.', 'wp-ai-connector')
            );
        }
    }

    private function is_wpgraphql_installed() {
        if (!function_exists('is_plugin_active')) {
            include_once(ABSPATH . 'wp-admin/includes/plugin.php');
        }
        return is_plugin_active(self::GRAPHQL_PLUGIN);
    }

    public function add_admin_menu() {
        add_options_page(
            __('Articulate Connector', 'wp-ai-connector'),
            __('Articulate Connector', 'wp-ai-connector'),
            'manage_options',
            'wp-ai-connector',
            [$this, 'render_admin_page']
        );
    }

    public function enqueue_admin_assets($hook) {
        if ($hook !== 'settings_page_wp-ai-connector') {
            return;
        }

        wp_enqueue_style(
            'wpai-connector-admin',
            plugins_url('assets/admin.css', __FILE__),
            [],
            '1.0.0'
        );

        wp_enqueue_script(
            'wpai-connector-admin',
            plugins_url('assets/admin.js', __FILE__),
            ['jquery'],
            '1.0.0',
            true
        );

        wp_localize_script('wpai-connector-admin', 'wpaiConnector', [
            'ajax_url' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('wpai_register_site'),
        ]);
    }

    public function render_admin_page() {
        $config = get_option(self::OPTION_NAME, []);
        $is_registered = !empty($config['registered']) && $config['registered'] === true;

        ?>
        <div class="wrap">
            <h1><?php _e('Articulate Connector', 'wp-ai-connector'); ?></h1>

            <?php if (!$this->is_wpgraphql_installed()): ?>
                <div class="notice notice-error">
                    <p>
                        <strong><?php _e('WPGraphQL Required', 'wp-ai-connector'); ?></strong><br>
                        <?php _e('This plugin requires WPGraphQL to function. Please install and activate the WPGraphQL plugin.', 'wp-ai-connector'); ?>
                    </p>
                    <p>
                        <a href="<?php echo esc_url(admin_url('plugin-install.php?s=wpgraphql&tab=search&type=term')); ?>" class="button button-primary">
                            <?php _e('Install WPGraphQL', 'wp-ai-connector'); ?>
                        </a>
                    </p>
                </div>
            <?php endif; ?>

            <?php if ($is_registered): ?>
                <div class="notice notice-success">
                    <p>
                        <strong><?php _e('✓ Connected to Articulate', 'wp-ai-connector'); ?></strong><br>
                        <?php
                        printf(
                            __('This site is registered with organization: <strong>%s</strong>', 'wp-ai-connector'),
                            esc_html($config['organization_name'] ?? 'Unknown')
                        );
                        ?>
                    </p>
                </div>

                <table class="form-table">
                    <tr>
                        <th scope="row"><?php _e('Organization', 'wp-ai-connector'); ?></th>
                        <td><?php echo esc_html($config['organization_name'] ?? 'N/A'); ?></td>
                    </tr>
                    <tr>
                        <th scope="row"><?php _e('Connection ID', 'wp-ai-connector'); ?></th>
                        <td><code><?php echo esc_html($config['connection_id'] ?? 'N/A'); ?></code></td>
                    </tr>
                    <tr>
                        <th scope="row"><?php _e('Registered At', 'wp-ai-connector'); ?></th>
                        <td><?php echo esc_html($config['registered_at'] ?? 'N/A'); ?></td>
                    </tr>
                    <tr>
                        <th scope="row"><?php _e('Site URL', 'wp-ai-connector'); ?></th>
                        <td><code><?php echo esc_url(home_url()); ?></code></td>
                    </tr>
                    <tr>
                        <th scope="row"><?php _e('GraphQL Endpoint', 'wp-ai-connector'); ?></th>
                        <td><code><?php echo esc_url(home_url('/graphql')); ?></code></td>
                    </tr>
                </table>

                <p class="description">
                    <?php _e('Your WordPress site is now connected to Articulate. You can manage content through the Articulate platform.', 'wp-ai-connector'); ?>
                </p>

                <hr>

                <h2><?php _e('Danger Zone', 'wp-ai-connector'); ?></h2>
                <p>
                    <button type="button" class="button button-secondary" id="wpai-disconnect">
                        <?php _e('Disconnect from Articulate', 'wp-ai-connector'); ?>
                    </button>
                </p>

            <?php else: ?>
                <form id="wpai-registration-form">
                    <table class="form-table">
                        <tr>
                            <th scope="row">
                                <label for="wpai-api-key"><?php _e('Organization API Key', 'wp-ai-connector'); ?> <span class="required">*</span></label>
                            </th>
                            <td>
                                <input type="password"
                                       id="wpai-api-key"
                                       name="api_key"
                                       class="regular-text code"
                                       placeholder="wpai_org_123_..."
                                       required>
                                <p class="description">
                                    <?php _e('Enter the organization API key from your Articulate dashboard. You can find this in Organization Settings → API Keys.', 'wp-ai-connector'); ?>
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <th scope="row">
                                <label for="wpai-site-name"><?php _e('Site Name', 'wp-ai-connector'); ?> <span class="required">*</span></label>
                            </th>
                            <td>
                                <input type="text"
                                       id="wpai-site-name"
                                       name="site_name"
                                       class="regular-text"
                                       value="<?php echo esc_attr(get_bloginfo('name')); ?>"
                                       required>
                                <p class="description">
                                    <?php _e('Friendly name for this connection (e.g., "Production Blog").', 'wp-ai-connector'); ?>
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <th scope="row">
                                <label for="wpai-username"><?php _e('WordPress Admin Username', 'wp-ai-connector'); ?> <span class="required">*</span></label>
                            </th>
                            <td>
                                <input type="text"
                                       id="wpai-username"
                                       name="wp_username"
                                       class="regular-text"
                                       value="<?php echo esc_attr(wp_get_current_user()->user_login); ?>"
                                       required>
                                <p class="description">
                                    <?php _e('WordPress username for Articulate to use (must have administrator privileges). An Application Password will be created for this user.', 'wp-ai-connector'); ?>
                                </p>
                            </td>
                        </tr>
                    </table>

                    <p class="submit">
                        <button type="submit" class="button button-primary" id="wpai-register-btn">
                            <?php _e('Register with Articulate', 'wp-ai-connector'); ?>
                        </button>
                        <span class="spinner" style="float: none; margin: 0 10px;"></span>
                    </p>

                    <div id="wpai-result" class="notice" style="display: none;"></div>
                </form>

                <div class="wpai-info-card">
                    <h3><?php _e('How It Works', 'wp-ai-connector'); ?></h3>
                    <ol>
                        <li><?php _e('Get an organization API key from your Articulate dashboard (Organization Settings → API Keys)', 'wp-ai-connector'); ?></li>
                        <li><?php _e('This plugin will automatically create an Application Password for secure API access', 'wp-ai-connector'); ?></li>
                        <li><?php _e('Your site will be registered with the organization and appear in the connections list', 'wp-ai-connector'); ?></li>
                        <li><?php _e('Articulate can now manage content on this WordPress site via GraphQL', 'wp-ai-connector'); ?></li>
                    </ol>

                    <h4><?php _e('Requirements', 'wp-ai-connector'); ?></h4>
                    <ul>
                        <li>✓ WordPress 5.6+ (for Application Password support)</li>
                        <li><?php echo $this->is_wpgraphql_installed() ? '✓' : '✗'; ?> WPGraphQL plugin installed and activated</li>
                        <li>✓ Administrator account</li>
                        <li>✓ Organization API key from Articulate</li>
                    </ul>
                </div>
            <?php endif; ?>
        </div>
        <?php
    }

    public function ajax_register_site() {
        check_ajax_referer('wpai_register_site', 'nonce');

        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => __('Insufficient permissions. You must be an administrator.', 'wp-ai-connector')]);
        }

        $api_key = sanitize_text_field($_POST['api_key'] ?? '');
        $site_name = sanitize_text_field($_POST['site_name'] ?? '');
        $wp_username = sanitize_text_field($_POST['wp_username'] ?? '');

        if (empty($api_key) || empty($site_name) || empty($wp_username)) {
            wp_send_json_error(['message' => __('All fields are required.', 'wp-ai-connector')]);
        }

        // Verify user exists and has admin capabilities
        $user = get_user_by('login', $wp_username);
        if (!$user || !user_can($user, 'manage_options')) {
            wp_send_json_error(['message' => __('User not found or lacks administrator privileges.', 'wp-ai-connector')]);
        }

        // Check WPGraphQL
        if (!$this->is_wpgraphql_installed()) {
            wp_send_json_error(['message' => __('WPGraphQL plugin is not active. Please install and activate WPGraphQL first.', 'wp-ai-connector')]);
        }

        // Create application password
        $app_password = $this->create_application_password($user->ID, 'Articulate Connector');
        if (is_wp_error($app_password)) {
            wp_send_json_error(['message' => $app_password->get_error_message()]);
        }

        // Prepare registration data
        $registration_data = [
            'api_key' => $api_key,
            'site_name' => $site_name,
            'wp_url' => home_url(),
            'wp_graphql_endpoint' => home_url('/graphql'),
            'wp_user' => $wp_username,
            'wp_app_password' => $app_password['password'],
        ];

        // Send to Articulate backend
        $response = wp_remote_post(self::API_ENDPOINT, [
            'body' => wp_json_encode($registration_data),
            'headers' => [
                'Content-Type' => 'application/json',
            ],
            'timeout' => 30,
            'sslverify' => false, // For local development
        ]);

        if (is_wp_error($response)) {
            // Clean up the app password we created
            $this->delete_application_password($user->ID, $app_password['uuid']);
            wp_send_json_error(['message' => __('Connection failed: ', 'wp-ai-connector') . $response->get_error_message()]);
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        $status_code = wp_remote_retrieve_response_code($response);

        if ($status_code !== 201) {
            // Clean up the app password we created
            $this->delete_application_password($user->ID, $app_password['uuid']);
            $error_msg = $body['error'] ?? __('Registration failed. Please check your API key and try again.', 'wp-ai-connector');
            wp_send_json_error(['message' => $error_msg]);
        }

        // Save registration config
        update_option(self::OPTION_NAME, [
            'registered' => true,
            'connection_id' => $body['connection_id'],
            'organization_id' => $body['organization']['id'],
            'organization_name' => $body['organization']['name'],
            'app_password_uuid' => $app_password['uuid'],
            'wp_user' => $wp_username,
            'registered_at' => current_time('mysql'),
        ]);

        wp_send_json_success([
            'message' => $body['message'] ?? __('Successfully registered with Articulate!', 'wp-ai-connector'),
            'organization' => $body['organization'],
        ]);
    }

    public function ajax_disconnect_site() {
        check_ajax_referer('wpai_register_site', 'nonce');

        if (!current_user_can('manage_options')) {
            wp_send_json_error(['message' => __('Insufficient permissions.', 'wp-ai-connector')]);
        }

        $config = get_option(self::OPTION_NAME, []);

        // Delete the application password if we have the UUID
        if (!empty($config['app_password_uuid']) && !empty($config['wp_user'])) {
            $user = get_user_by('login', $config['wp_user']);
            if ($user) {
                $this->delete_application_password($user->ID, $config['app_password_uuid']);
            }
        }

        // Clear the configuration
        delete_option(self::OPTION_NAME);

        wp_send_json_success(['message' => __('Successfully disconnected from Articulate.', 'wp-ai-connector')]);
    }

    private function create_application_password($user_id, $name) {
        if (!function_exists('wp_generate_application_password')) {
            return new WP_Error(
                'app_password_unavailable',
                __('Application passwords are not available. Requires WordPress 5.6+.', 'wp-ai-connector')
            );
        }

        $app_password = wp_generate_application_password($user_id, $name);

        if (is_wp_error($app_password)) {
            return $app_password;
        }

        return $app_password;
    }

    private function delete_application_password($user_id, $uuid) {
        if (!function_exists('wp_delete_application_password')) {
            return false;
        }

        return wp_delete_application_password($user_id, $uuid);
    }

    private function add_notice($type, $message) {
        $this->admin_notices[] = [
            'type' => $type,
            'message' => $message,
        ];
    }

    public function display_admin_notices() {
        foreach ($this->admin_notices as $notice) {
            printf(
                '<div class="notice notice-%s is-dismissible"><p>%s</p></div>',
                esc_attr($notice['type']),
                esc_html($notice['message'])
            );
        }
    }
}

// Initialize the plugin
new WP_AI_Connector();
