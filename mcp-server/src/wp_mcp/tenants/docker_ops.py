"""Docker operations for tenant lifecycle management."""

import logging
from python_on_whales import DockerClient

logger = logging.getLogger(__name__)


class TenantDockerOps:
    """Manages Docker Compose projects for tenants."""

    def __init__(self, compose_dir: str | None = None):
        self.compose_dir = compose_dir
        self.docker = DockerClient()

    def project_name(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    def container_name(self, tenant_id: str, service: str) -> str:
        return f"tenant_{tenant_id}_{service}"

    def up(self, tenant_id: str, compose_file: str) -> None:
        """Start a tenant's Docker Compose project."""
        project = self.project_name(tenant_id)
        logger.info("Starting tenant %s from %s", tenant_id, compose_file)
        self.docker.compose.up(
            compose_files=[compose_file],
            project_name=project,
            detach=True,
            build=False,
            quiet=True,
        )
        logger.info("Tenant %s started", tenant_id)

    def down(self, tenant_id: str, compose_file: str | None = None, volumes: bool = False) -> None:
        """Stop and remove a tenant's Docker Compose project."""
        project = self.project_name(tenant_id)
        logger.info("Stopping tenant %s (volumes=%s)", tenant_id, volumes)
        kwargs: dict = {"project_name": project, "volumes": volumes}
        if compose_file:
            kwargs["compose_files"] = [compose_file]
        self.docker.compose.down(**kwargs)
        logger.info("Tenant %s stopped", tenant_id)

    def status(self, tenant_id: str, compose_file: str | None = None) -> dict[str, str]:
        """Get status of all containers in a tenant project."""
        project = self.project_name(tenant_id)
        kwargs: dict = {"project_name": project}
        if compose_file:
            kwargs["compose_files"] = [compose_file]
        try:
            containers = self.docker.compose.ps(**kwargs)
            return {c.name: c.state.status for c in containers}
        except Exception as e:
            logger.error("Failed to get status for tenant %s: %s", tenant_id, e)
            return {}

    def is_healthy(self, tenant_id: str) -> bool:
        """Check if the tenant's WordPress container is running."""
        statuses = self.status(tenant_id)
        wp_name = self.container_name(tenant_id, "wordpress")
        return statuses.get(wp_name) == "running"
