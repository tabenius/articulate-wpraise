<?php
/**
 * Plugin Name: WP-AI Authentication
 * Description: JWT-based authentication for WP-AI application
 * Version: 1.0.0
 * Author: WP-AI Team
 */

if (!defined('ABSPATH')) {
    exit;
}

class WP_AI_Auth {
    private $secret_key;
    private $token_expiration = 7 * DAY_IN_SECONDS; // 7 days

    public function __construct() {
        $this->secret_key = AUTH_KEY;
        $this->register_rest_routes();
        $this->register_admin_customizations();
    }

    public function register_admin_customizations() {
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_styles']);
    }

    public function enqueue_admin_styles() {
        wp_add_inline_style('common', $this->get_admin_custom_css());
    }

    private function get_admin_custom_css() {
        return "
            /* Fix WordPress admin menu opacity */
            #adminmenuback,
            #adminmenuwrap,
            #adminmenu,
            #adminmenu .wp-submenu {
                background-color: #23282d !important;
                opacity: 1 !important;
            }

            #adminmenu .wp-submenu {
                background-color: #32373c !important;
            }

            /* Ensure menu text is readable */
            #adminmenu a {
                color: #eee !important;
            }

            #adminmenu .wp-submenu a {
                color: #b4b9be !important;
            }

            /* Responsive zoom support - scale UI elements properly */
            @media (min-width: 1200px) {
                body {
                    font-size: 13px;
                }

                #wpcontent,
                #wpfooter {
                    margin-left: 160px;
                }

                #adminmenuback,
                #adminmenuwrap,
                #adminmenu {
                    width: 160px;
                }

                /* Adjust content area for better fit */
                .wrap {
                    margin: 10px 20px 0 2px;
                }
            }

            /* Better responsive behavior at different zoom levels */
            @media (max-width: 1600px) {
                .wp-list-table {
                    font-size: 12px;
                }

                .wrap h1 {
                    font-size: 1.8em;
                }
            }

            @media (max-width: 1400px) {
                .wp-list-table {
                    font-size: 11px;
                }

                input[type='text'],
                input[type='email'],
                input[type='url'],
                input[type='password'],
                textarea,
                select {
                    font-size: 13px;
                    padding: 3px 5px;
                }
            }

            /* Ensure tables don't overflow at 90% zoom */
            .wp-list-table {
                max-width: 100%;
                overflow-x: auto;
            }

            /* Better column sizing */
            .wp-list-table th,
            .wp-list-table td {
                padding: 8px 10px;
            }

            /* Scrollable table wrapper for narrow screens */
            .tablenav {
                clear: both;
                margin: 6px 0 4px;
            }
        ";
    }

    public function register_rest_routes() {
        add_action('rest_api_init', function() {
            // Login endpoint
            register_rest_route('wp-ai/v1', '/auth/login', [
                'methods' => 'POST',
                'callback' => [$this, 'handle_login'],
                'permission_callback' => '__return_true',
            ]);

            // Token verification endpoint
            register_rest_route('wp-ai/v1', '/auth/verify', [
                'methods' => 'POST',
                'callback' => [$this, 'handle_verify'],
                'permission_callback' => '__return_true',
            ]);

            // Get current user endpoint (protected)
            register_rest_route('wp-ai/v1', '/auth/me', [
                'methods' => 'GET',
                'callback' => [$this, 'handle_me'],
                'permission_callback' => [$this, 'verify_token_permission'],
            ]);

            // Logout endpoint
            register_rest_route('wp-ai/v1', '/auth/logout', [
                'methods' => 'POST',
                'callback' => [$this, 'handle_logout'],
                'permission_callback' => [$this, 'verify_token_permission'],
            ]);
        });
    }

    public function handle_login($request) {
        $username = $request->get_param('username');
        $password = $request->get_param('password');

        if (empty($username) || empty($password)) {
            return new WP_Error(
                'missing_credentials',
                'Username and password are required',
                ['status' => 400]
            );
        }

        // Authenticate user
        $user = wp_authenticate($username, $password);

        if (is_wp_error($user)) {
            return new WP_Error(
                'invalid_credentials',
                'Invalid username or password',
                ['status' => 401]
            );
        }

        // Generate JWT token
        $token = $this->generate_token($user);

        return rest_ensure_response([
            'success' => true,
            'token' => $token,
            'user' => [
                'id' => $user->ID,
                'username' => $user->user_login,
                'email' => $user->user_email,
                'displayName' => $user->display_name,
                'roles' => $user->roles,
            ],
            'expiresAt' => time() + $this->token_expiration,
        ]);
    }

    public function handle_verify($request) {
        $token = $this->get_token_from_request($request);

        if (!$token) {
            return new WP_Error(
                'no_token',
                'No token provided',
                ['status' => 401]
            );
        }

        $payload = $this->verify_token($token);

        if (!$payload) {
            return new WP_Error(
                'invalid_token',
                'Invalid or expired token',
                ['status' => 401]
            );
        }

        $user = get_user_by('id', $payload['user_id']);

        if (!$user) {
            return new WP_Error(
                'user_not_found',
                'User not found',
                ['status' => 404]
            );
        }

        return rest_ensure_response([
            'success' => true,
            'valid' => true,
            'user' => [
                'id' => $user->ID,
                'username' => $user->user_login,
                'email' => $user->user_email,
                'displayName' => $user->display_name,
                'roles' => $user->roles,
            ],
        ]);
    }

    public function handle_me($request) {
        $user_id = $this->get_user_id_from_token($request);
        $user = get_user_by('id', $user_id);

        if (!$user) {
            return new WP_Error(
                'user_not_found',
                'User not found',
                ['status' => 404]
            );
        }

        return rest_ensure_response([
            'id' => $user->ID,
            'username' => $user->user_login,
            'email' => $user->user_email,
            'displayName' => $user->display_name,
            'roles' => $user->roles,
        ]);
    }

    public function handle_logout($request) {
        // In a stateless JWT system, logout is handled client-side
        // by removing the token. We can add token blacklisting here if needed.
        return rest_ensure_response([
            'success' => true,
            'message' => 'Logged out successfully',
        ]);
    }

    private function generate_token($user) {
        $issued_at = time();
        $expiration = $issued_at + $this->token_expiration;

        $payload = [
            'iss' => get_bloginfo('url'),
            'iat' => $issued_at,
            'exp' => $expiration,
            'user_id' => $user->ID,
            'username' => $user->user_login,
        ];

        return $this->encode_jwt($payload);
    }

    private function verify_token($token) {
        try {
            $payload = $this->decode_jwt($token);

            // Check expiration
            if (isset($payload['exp']) && $payload['exp'] < time()) {
                return false;
            }

            return $payload;
        } catch (Exception $e) {
            return false;
        }
    }

    public function verify_token_permission($request) {
        $token = $this->get_token_from_request($request);

        if (!$token) {
            return false;
        }

        $payload = $this->verify_token($token);
        return $payload !== false;
    }

    private function get_user_id_from_token($request) {
        $token = $this->get_token_from_request($request);

        if (!$token) {
            return null;
        }

        $payload = $this->verify_token($token);

        if (!$payload || !isset($payload['user_id'])) {
            return null;
        }

        return $payload['user_id'];
    }

    private function get_token_from_request($request) {
        // Try Authorization header first
        $auth_header = $request->get_header('authorization');
        if ($auth_header && preg_match('/Bearer\s+(.+)/', $auth_header, $matches)) {
            return $matches[1];
        }

        // Try custom header
        $token = $request->get_header('X-WP-AI-Token');
        if ($token) {
            return $token;
        }

        // Try query parameter
        return $request->get_param('token');
    }

    private function encode_jwt($payload) {
        $header = json_encode(['typ' => 'JWT', 'alg' => 'HS256']);
        $payload = json_encode($payload);

        $base64_header = $this->base64_url_encode($header);
        $base64_payload = $this->base64_url_encode($payload);

        $signature = hash_hmac(
            'sha256',
            $base64_header . '.' . $base64_payload,
            $this->secret_key,
            true
        );
        $base64_signature = $this->base64_url_encode($signature);

        return $base64_header . '.' . $base64_payload . '.' . $base64_signature;
    }

    private function decode_jwt($jwt) {
        $parts = explode('.', $jwt);

        if (count($parts) !== 3) {
            throw new Exception('Invalid token format');
        }

        list($base64_header, $base64_payload, $base64_signature) = $parts;

        // Verify signature
        $signature = hash_hmac(
            'sha256',
            $base64_header . '.' . $base64_payload,
            $this->secret_key,
            true
        );
        $expected_signature = $this->base64_url_encode($signature);

        if ($base64_signature !== $expected_signature) {
            throw new Exception('Invalid signature');
        }

        // Decode payload
        $payload = json_decode($this->base64_url_decode($base64_payload), true);

        if (!$payload) {
            throw new Exception('Invalid payload');
        }

        return $payload;
    }

    private function base64_url_encode($data) {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    private function base64_url_decode($data) {
        return base64_decode(strtr($data, '-_', '+/'));
    }
}

// Initialize the plugin
new WP_AI_Auth();
