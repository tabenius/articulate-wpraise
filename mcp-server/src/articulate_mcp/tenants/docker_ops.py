"""Docker operations for tenant lifecycle management."""

import logging
from python_on_whales import DockerClient

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
