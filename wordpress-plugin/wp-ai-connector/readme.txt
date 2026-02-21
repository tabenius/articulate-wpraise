=== Articulate Connector ===
Contributors: wpaiteam
Tags: ai, content, graphql, automation, management
Requires at least: 5.6
Tested up to: 6.4
Requires PHP: 7.4
Stable tag: 1.0.0
License: GPLv2 or later
License URI: http://www.gnu.org/licenses/gpl-2.0.html

Connect your WordPress site to the Articulate platform for AI-powered content management.

== Description ==

Articulate Connector automatically registers your WordPress site with the Articulate platform, enabling AI-powered content creation, editing, and management through a modern web interface.

= Features =

* **One-Click Registration**: Register your site with an organization API key
* **Automatic Setup**: Creates Application Password for secure API access
* **WPGraphQL Integration**: Requires and works with WPGraphQL for efficient data access
* **Secure**: Uses WordPress Application Passwords (WordPress 5.6+)
* **Organization Support**: Connect sites to team organizations

= Requirements =

* WordPress 5.6 or higher
* PHP 7.4 or higher
* WPGraphQL plugin installed and activated
* Administrator account
* Organization API key from Articulate platform

== Installation ==

1. Upload the `articulate-connector` folder to the `/wp-content/plugins/` directory
2. Activate the plugin through the 'Plugins' menu in WordPress
3. Install and activate WPGraphQL if not already installed
4. Navigate to Settings → Articulate Connector
5. Enter your organization API key from the Articulate dashboard
6. Click "Register with Articulate"

== Frequently Asked Questions ==

= What is Articulate? =

Articulate is a modern platform for managing WordPress content using AI assistance. It provides a clean web interface for creating, editing, and managing posts, pages, and other content.

= Do I need WPGraphQL? =

Yes, WPGraphQL is required for Articulate to communicate with your WordPress site efficiently.

= Is my data secure? =

Yes. The plugin uses WordPress Application Passwords, which are secure, revocable API credentials. No passwords are stored or transmitted.

= Can I disconnect my site later? =

Yes, you can disconnect at any time from the plugin settings page. This will revoke the Application Password and remove the connection.

= What is an organization API key? =

An organization API key is a single-use registration token generated from the Articulate platform. Get one from your organization settings in the Articulate dashboard.

== Changelog ==

= 1.0.0 =
* Initial release
* Organization API key registration
* Automatic Application Password creation
* WPGraphQL integration
* Secure connection management
