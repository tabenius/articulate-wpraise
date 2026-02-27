#!/usr/bin/env python3
"""
Remote WordPress Setup Script using SSH
Sets up a remote WordPress instance for WP-AI MCP Server integration.

Requirements:
- paramiko: pip install paramiko
- WP-CLI installed on remote server
- SSH access to remote server

Usage:
    python setup-remote-wordpress.py --host example.com --user ubuntu --key ~/.ssh/id_rsa
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed. Run: pip install paramiko")
    sys.exit(1)


class WordPressRemoteSetup:
    """Setup remote WordPress for WP-AI integration."""

    def __init__(self, host: str, user: str, port: int = 22,
                 key_path: Optional[str] = None, password: Optional[str] = None):
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.password = password
        self.ssh_client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """Establish SSH connection."""
        print(f"🔌 Connecting to {self.user}@{self.host}:{self.port}...")

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if self.key_path:
                key = paramiko.RSAKey.from_private_key_file(self.key_path)
                self.ssh_client.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    pkey=key
                )
            else:
                self.ssh_client.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password
                )
            print("✅ Connected successfully")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def execute_command(self, command: str, check_error: bool = True) -> tuple[int, str, str]:
        """Execute command on remote server."""
        if not self.ssh_client:
            raise RuntimeError("Not connected to SSH server")

        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if check_error and exit_code != 0:
            raise RuntimeError(f"Command failed: {command}\nError: {error}")

        return exit_code, output, error

    def find_all_wordpress_installations(self) -> list[str]:
        """Find all WordPress installations on server.

        Returns:
            List of WordPress installation paths
        """
        print("🔍 Searching for WordPress installations...")

        if not self.ssh_client:
            return []

        found_installations = []

        # Common WordPress paths
        common_paths = [
            "/var/www/html",
            "/var/www/wordpress",
            "/var/www",
            "/usr/share/nginx/html",
            "/home/*/public_html",
            "/opt/wordpress",
        ]

        for path in common_paths:
            try:
                # Handle wildcard paths
                if '*' in path:
                    _, output, _ = self.execute_command(
                        f"find {path.rsplit('/*', 1)[0]} -maxdepth 2 -name wp-config.php 2>/dev/null | head -5",
                        check_error=False
                    )
                    if output:
                        for line in output.strip().split('\n'):
                            if line:
                                wp_dir = line.rsplit('/', 1)[0]
                                if wp_dir not in found_installations:
                                    found_installations.append(wp_dir)
                else:
                    exit_code, _, _ = self.execute_command(
                        f"test -f {path}/wp-config.php",
                        check_error=False
                    )
                    if exit_code == 0 and path not in found_installations:
                        found_installations.append(path)
            except Exception as e:
                logger.debug(f"Error checking path {path}: {e}")
                continue

        # Also try comprehensive search (defensive: limit results)
        try:
            _, output, _ = self.execute_command(
                "find /var/www /home /opt -maxdepth 4 -name wp-config.php 2>/dev/null | head -10",
                check_error=False
            )
            if output:
                for line in output.strip().split('\n'):
                    if line:
                        wp_dir = line.rsplit('/', 1)[0]
                        if wp_dir not in found_installations:
                            found_installations.append(wp_dir)
        except Exception as e:
            logger.debug(f"Error in comprehensive search: {e}")

        if found_installations:
            print(f"✅ Found {len(found_installations)} WordPress installation(s)")
            for path in found_installations:
                print(f"   - {path}")
        else:
            print("❌ No WordPress installations found")

        return found_installations

    def find_wordpress_path(self, specified_path: Optional[str] = None) -> Optional[str]:
        """Find WordPress installation path.

        Args:
            specified_path: Optional specific path to WordPress installation

        Returns:
            WordPress path or None
        """
        # Defensive: validate specified path
        if specified_path:
            # Sanitize path (basic security check)
            if not specified_path.startswith('/'):
                print(f"❌ Invalid path: must be absolute path")
                return None

            # Verify specified path has WordPress
            try:
                exit_code, _, _ = self.execute_command(
                    f"test -f {specified_path}/wp-config.php",
                    check_error=False
                )
                if exit_code == 0:
                    print(f"✅ WordPress found at specified path: {specified_path}")
                    return specified_path
                else:
                    print(f"❌ No WordPress found at {specified_path}")
                    return None
            except Exception as e:
                print(f"❌ Error verifying path {specified_path}: {e}")
                return None
        else:
            # Search for installations
            installations = self.find_all_wordpress_installations()
            if len(installations) > 0:
                # Return first found installation
                return installations[0]
            return None

    def check_wp_cli(self) -> bool:
        """Check if WP-CLI is installed."""
        print("🔍 Checking for WP-CLI...")
        try:
            exit_code, output, _ = self.execute_command("wp --version", check_error=False)
            if exit_code == 0:
                print(f"✅ WP-CLI found: {output}")
                return True
            else:
                print("❌ WP-CLI not installed")
                return False
        except:
            print("❌ WP-CLI not installed")
            return False

    def install_plugin(self, wp_path: str, plugin_slug: str) -> bool:
        """Install and activate WordPress plugin."""
        print(f"📦 Installing plugin: {plugin_slug}...")

        try:
            # Check if already installed
            exit_code, _, _ = self.execute_command(
                f"wp --path={wp_path} plugin is-installed {plugin_slug}",
                check_error=False
            )

            if exit_code == 0:
                print(f"   Plugin {plugin_slug} already installed")
            else:
                # Install plugin
                self.execute_command(f"wp --path={wp_path} plugin install {plugin_slug} --activate")
                print(f"✅ Installed and activated {plugin_slug}")

            # Ensure it's activated
            self.execute_command(f"wp --path={wp_path} plugin activate {plugin_slug}")
            return True

        except Exception as e:
            print(f"❌ Failed to install {plugin_slug}: {e}")
            return False

    def create_mcp_user(self, wp_path: str, username: str = "mcp-api-user") -> Optional[dict]:
        """Create WordPress user with application password for MCP access."""
        print(f"👤 Creating MCP API user: {username}...")

        try:
            # Check if user exists
            exit_code, _, _ = self.execute_command(
                f"wp --path={wp_path} user get {username}",
                check_error=False
            )

            user_id = None
            if exit_code == 0:
                print(f"   User {username} already exists")
                _, output, _ = self.execute_command(
                    f"wp --path={wp_path} user get {username} --field=ID"
                )
                user_id = output.strip()
            else:
                # Create user with administrator role
                _, output, _ = self.execute_command(
                    f"wp --path={wp_path} user create {username} {username}@mcp-server.local "
                    f"--role=administrator --user_pass=$(openssl rand -base64 32)"
                )
                # Extract user ID from output
                user_id = output.split()[-1].strip('.')
                print(f"✅ Created user {username} (ID: {user_id})")

            # Create application password
            print("🔑 Generating application password...")
            _, app_password_raw, _ = self.execute_command(
                f"wp --path={wp_path} user application-password create {user_id} 'MCP-Server-Access' --porcelain"
            )
            app_password = app_password_raw.strip()

            if not app_password:
                raise RuntimeError("Failed to create application password")

            print(f"✅ Application password created: {app_password[:8]}...")

            return {
                "username": username,
                "user_id": user_id,
                "app_password": app_password
            }

        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return None

    def get_site_info(self, wp_path: str) -> dict:
        """Get WordPress site information."""
        print("ℹ️  Getting site information...")

        try:
            _, url_output, _ = self.execute_command(
                f"wp --path={wp_path} option get siteurl"
            )
            site_url = url_output.strip()

            _, title_output, _ = self.execute_command(
                f"wp --path={wp_path} option get blogname"
            )
            site_title = title_output.strip()

            return {
                "url": site_url,
                "title": site_title,
                "graphql_endpoint": f"{site_url}/graphql"
            }
        except Exception as e:
            print(f"⚠️  Could not get site info: {e}")
            return {
                "url": f"http://{self.host}",
                "title": "WordPress Site",
                "graphql_endpoint": f"http://{self.host}/graphql"
            }

    def enable_graphql_jwt(self, wp_path: str) -> bool:
        """Configure WPGraphQL JWT Authentication."""
        print("🔐 Configuring WPGraphQL JWT Authentication...")

        try:
            # Generate secret key
            _, secret_key, _ = self.execute_command("openssl rand -base64 32")
            secret_key = secret_key.strip()

            # Add configuration to wp-config.php
            wp_config_additions = f"""
// WPGraphQL JWT Authentication configuration
define('GRAPHQL_JWT_AUTH_SECRET_KEY', '{secret_key}');
define('JWT_AUTH_CORS_ENABLE', true);
"""

            # Check if already configured
            exit_code, _, _ = self.execute_command(
                f"grep -q 'GRAPHQL_JWT_AUTH_SECRET_KEY' {wp_path}/wp-config.php",
                check_error=False
            )

            if exit_code != 0:
                # Add before "/* That's all" line
                self.execute_command(
                    f"sed -i \"/That's all/i {wp_config_additions}\" {wp_path}/wp-config.php"
                )
                print("✅ JWT Authentication configured")
            else:
                print("   JWT Authentication already configured")

            return True

        except Exception as e:
            print(f"⚠️  JWT configuration warning: {e}")
            return False

    def discover_installations(self) -> Optional[dict]:
        """Discover WordPress installations on remote server.

        Returns:
            Dict with list of found installations
        """
        print("\n🔍 Discovering WordPress Installations\n")

        if not self.connect():
            return None

        try:
            installations = self.find_all_wordpress_installations()

            return {
                "installations": installations,
                "count": len(installations)
            }

        except Exception as e:
            print(f"\n❌ Discovery failed: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self.disconnect()

    def setup(self, wp_path: Optional[str] = None) -> Optional[dict]:
        """Run complete WordPress setup for MCP integration.

        Args:
            wp_path: Optional WordPress installation path

        Returns:
            Connection info dict or None
        """
        print("\n🚀 Starting WordPress Remote Setup for WP-AI MCP Integration\n")

        if not self.connect():
            return None

        try:
            # Check WP-CLI
            if not self.check_wp_cli():
                print("\n❌ WP-CLI is required but not installed on remote server")
                print("   Install it: https://wp-cli.org/")
                return None

            # Find WordPress (use specified path or search)
            if wp_path:
                found_wp_path = self.find_wordpress_path(wp_path)
            else:
                found_wp_path = self.find_wordpress_path()

            if not found_wp_path:
                print("\n❌ Could not locate WordPress installation")
                return None

            wp_path = found_wp_path

            # Install required plugins
            required_plugins = [
                "wp-graphql",
                "wp-graphql-jwt-authentication"
            ]

            # Allow additional plugins via CLI flag
            if hasattr(self, 'extra_plugins_to_install') and self.extra_plugins_to_install:
                for p in self.extra_plugins_to_install:
                    if p and p not in required_plugins:
                        required_plugins.append(p)

            for plugin in required_plugins:
                self.install_plugin(wp_path, plugin)

            # Configure JWT
            self.enable_graphql_jwt(wp_path)

            # Create MCP user
            user_info = self.create_mcp_user(wp_path)
            if not user_info:
                return None

            # Get site info
            site_info = self.get_site_info(wp_path)

            # Compile connection info
            connection_info = {
                "name": f"{site_info['title']} ({self.host})",
                "wp_url": site_info["url"],
                "wp_graphql_endpoint": site_info["graphql_endpoint"],
                "wp_user": user_info["username"],
                "wp_app_password": user_info["app_password"],
                "host": self.host,
                "setup_timestamp": __import__('datetime').datetime.now().isoformat()
            }

            print("\n" + "="*60)
            print("✅ WordPress Setup Complete!")
            print("="*60)
            print("\nConnection Details:")
            print(json.dumps(connection_info, indent=2))
            print("\nYou can now add this connection to your WP-AI MCP Server.")
            print("="*60 + "\n")

            return connection_info

        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self.disconnect()

    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            print("🔌 Disconnected from server")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup remote WordPress for WP-AI MCP Server integration"
    )
    parser.add_argument("--host", required=True, help="Remote server hostname or IP")
    parser.add_argument("--user", required=True, help="SSH username")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--key", help="Path to SSH private key file")
    parser.add_argument("--password", help="SSH password (not recommended, use --key instead)")
    parser.add_argument("--wp-path", help="WordPress installation directory path")
    parser.add_argument("--discover", action="store_true", help="Only discover WordPress installations (don't setup)")
    parser.add_argument("--username", default="mcp-api-user", help="WordPress username to create")
    parser.add_argument("--output", help="Save connection info to JSON file")
    parser.add_argument("--plugins", help="Comma-separated plugin slugs to install (e.g., learnpress,other-plugin)")

    args = parser.parse_args()

    if not args.key and not args.password:
        print("❌ Error: Must provide either --key or --password")
        sys.exit(1)

    # Create setup instance
    setup = WordPressRemoteSetup(
        host=args.host,
        user=args.user,
        port=args.port,
        key_path=args.key,
        password=args.password
    )

    # Pass extra plugins to install into the setup instance
    if args.plugins:
        setup.extra_plugins_to_install = [p.strip() for p in args.plugins.split(',') if p.strip()]

    # Run discover mode or full setup
    if args.discover:
        result = setup.discover_installations()
        if result:
            print(f"\n✅ Found {result['count']} WordPress installation(s)")
            if args.output:
                output_path = Path(args.output)
                output_path.write_text(json.dumps(result, indent=2))
                print(f"💾 Discovery results saved to: {output_path}")
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        connection_info = setup.setup(wp_path=args.wp_path)

    if connection_info:
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json.dumps(connection_info, indent=2))
            print(f"💾 Connection info saved to: {output_path}")

        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
