"""Render per-tenant docker-compose YAML from Jinja2 templates."""

import os
from jinja2 import Environment, FileSystemLoader


class TenantComposer:
    """Renders docker-compose files for tenant stacks."""

    def __init__(self, template_dir: str | None = None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "templates")
        self.template_dir = os.path.abspath(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=False,
            keep_trailing_newline=True,
        )

    def render(
        self,
        tenant_id: str,
        tenant_name: str,
        db_password: str,
        db_root_password: str,
        template_name: str = "docker-compose-tenant.yml",
    ) -> str:
        template = self.env.get_template(template_name)
        return template.render(
            TENANT_ID=tenant_id,
            TENANT_NAME=tenant_name,
            DB_PASSWORD=db_password,
            DB_ROOT_PASSWORD=db_root_password,
        )

    def save(self, rendered: str, tenant_name: str, output_dir: str | None = None) -> str:
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(self.template_dir), "tenants")
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"docker-compose-{tenant_name}.yml")
        with open(path, "w") as f:
            f.write(rendered)
        return path
