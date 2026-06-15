"""Docker operations for tenant lifecycle management."""

import logging
import time
from python_on_whales import DockerClient, docker as global_docker

logger = logging.getLogger(__name__)


class TenantDockerOps:
    """Manages Docker Compose projects for tenants."""

    def __init__(self, compose_dir: str | None = None):
        self.compose_dir = compose_dir

    def _client(self, tenant_id: str, compose_file: str | None = None) -> DockerClient:
        """Create a DockerClient configured for a specific tenant project."""
        kwargs: dict = {"compose_project_name": f"tenant_{tenant_id}"}
        if compose_file:
            kwargs["compose_files"] = [compose_file]
        return DockerClient(**kwargs)

    def project_name(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    def container_name(self, tenant_id: str, service: str) -> str:
        return f"tenant_{tenant_id}_{service}"

    def up(self, tenant_id: str, compose_file: str) -> None:
        """Start a tenant's Docker Compose project."""
        logger.info("Starting tenant %s from %s", tenant_id, compose_file)
        client = self._client(tenant_id, compose_file)
        client.compose.up(detach=True, build=False, quiet=True)
        logger.info("Tenant %s started", tenant_id)

    def down(self, tenant_id: str, compose_file: str | None = None, volumes: bool = False) -> None:
        """Stop and remove a tenant's Docker Compose project."""
        logger.info("Stopping tenant %s (volumes=%s)", tenant_id, volumes)
        client = self._client(tenant_id, compose_file)
        client.compose.down(volumes=volumes)
        logger.info("Tenant %s stopped", tenant_id)

    def status(self, tenant_id: str, compose_file: str | None = None) -> dict[str, str]:
        """Get status of all containers in a tenant project."""
        try:
            client = self._client(tenant_id, compose_file)
            containers = client.compose.ps()
            return {c.name: c.state.status for c in containers}
        except Exception as e:
            logger.error("Failed to get status for tenant %s: %s", tenant_id, e)
            return {}

    def is_healthy(self, tenant_id: str) -> bool:
        """Check if the tenant's WordPress container is running."""
        statuses = self.status(tenant_id)
        wp_name = self.container_name(tenant_id, "wordpress")
        return statuses.get(wp_name) == "running"

    def _exec(self, container_name: str, command: list[str]) -> str:
        """Execute a command in a running container and return stdout."""
        return global_docker.execute(container_name, command)

    def setup_wordpress(
        self,
        tenant_id: str,
        tenant_name: str,
        admin_password: str,
        admin_email: str = "",
        base_domain: str = "ragbaz.cc",
    ) -> str | None:
        """Install WordPress core, plugins, and mu-plugins in a tenant container.

        Returns the application password for MCP access, or None on failure.
        """
        wp_container = self.container_name(tenant_id, "wordpress")
        site_url = f"https://wordpress-{tenant_name}.{base_domain}"

        if not admin_email:
            admin_email = f"admin@{tenant_name}.{base_domain}"

        # Wait for WordPress HTTP endpoint (up to 60s)
        for attempt in range(30):
            try:
                output = self._exec(wp_container, [
                    "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/"
                ])
                if output.strip() in ("200", "302", "301"):
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            logger.error("Tenant %s: WordPress HTTP not ready after 60s", tenant_id)
            return None

        # Install wp-cli
        try:
            self._exec(wp_container, ["bash", "-c",
                "curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar "
                "&& chmod +x wp-cli.phar && mv wp-cli.phar /usr/local/bin/wp"
            ])
        except Exception as e:
            logger.error("Tenant %s: Failed to install wp-cli: %s", tenant_id, e)
            return None

        # Install WordPress core
        try:
            self._exec(wp_container, [
                "wp", "core", "install",
                f"--url={site_url}",
                f"--title={tenant_name}",
                "--admin_user=admin",
                f"--admin_password={admin_password}",
                f"--admin_email={admin_email}",
                "--skip-email",
                "--allow-root",
            ])
            logger.info("Tenant %s: WordPress core installed", tenant_id)
        except Exception as e:
            logger.error("Tenant %s: wp core install failed: %s", tenant_id, e)
            return None

        # Configure permalinks (required for WPGraphQL)
        try:
            self._exec(wp_container, [
                "wp", "rewrite", "structure", "/%postname%/", "--allow-root"
            ])
            self._exec(wp_container, ["wp", "rewrite", "flush", "--allow-root"])
        except Exception as e:
            logger.warning("Tenant %s: permalink setup failed: %s", tenant_id, e)

        # Install WPGraphQL
        try:
            self._exec(wp_container, [
                "wp", "plugin", "install", "wp-graphql", "--activate", "--allow-root"
            ])
            logger.info("Tenant %s: WPGraphQL installed", tenant_id)
        except Exception as e:
            logger.error("Tenant %s: WPGraphQL install failed: %s", tenant_id, e)
            return None

        # Install WPGraphQL Content Blocks (non-critical)
        try:
            self._exec(wp_container, ["bash", "-c",
                "curl -sL -o /tmp/cb.zip "
                "'https://github.com/wpengine/wp-graphql-content-blocks/releases/latest/download/wp-graphql-content-blocks.zip' "
                "&& wp plugin install /tmp/cb.zip --activate --allow-root "
                "&& rm -f /tmp/cb.zip"
            ])
            logger.info("Tenant %s: WPGraphQL Content Blocks installed", tenant_id)
        except Exception as e:
            logger.warning("Tenant %s: Content Blocks install failed (non-critical): %s", tenant_id, e)

        # Create mu-plugins
        try:
            self._exec(wp_container, ["bash", "-c", """
mkdir -p /var/www/html/wp-content/mu-plugins
cat > /var/www/html/wp-content/mu-plugins/enable-graphql-introspection.php << 'EOF'
<?php
/* Plugin Name: Enable GraphQL Introspection */
add_filter('graphql_introspection_enabled', '__return_true');
EOF
cat > /var/www/html/wp-content/mu-plugins/enable-app-passwords.php << 'EOF'
<?php
/* Plugin Name: Enable App Passwords */
add_filter('wp_is_application_passwords_available', '__return_true');
add_filter('wp_is_application_passwords_available_for_user', '__return_true');
EOF
"""])
        except Exception as e:
            logger.warning("Tenant %s: mu-plugins setup failed: %s", tenant_id, e)

        # Create application password for MCP access
        try:
            app_password = self._exec(wp_container, [
                "wp", "user", "application-password", "create",
                "admin", "articulate-mcp", "--porcelain", "--allow-root"
            ])
            app_password = app_password.strip()
            logger.info("Tenant %s: Application password created", tenant_id)
            return app_password
        except Exception as e:
            logger.error("Tenant %s: App password creation failed: %s", tenant_id, e)
            return None
