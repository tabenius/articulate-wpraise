<?php
/**
 * Plugin Name: Enable Application Passwords
 * Description: Enable Application Passwords for HTTP (local development)
 * Version: 1.0.0
 */

// Enable Application Passwords even over HTTP for local development
add_filter( 'wp_is_application_passwords_available', '__return_true' );
