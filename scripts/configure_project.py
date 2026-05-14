#!/usr/bin/env python3
"""Interactive project configuration REPL for WP-AI.

This script manages:
- /home/xyzzy/wp-ai/.env
- /home/xyzzy/wp-ai/web/.env.local

It provides:
- variable meaning
- where to find each key/value
- interactive REPL for setting and saving values
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class ConfigVar:
    name: str
    target: str  # "root" | "web"
    required: bool
    description: str
    where_to_find: str
    default: str = ""
    secret: bool = False


ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV_DEFAULT = ROOT / ".env"
ROOT_ENV_EXAMPLE = ROOT / ".env.example"
WEB_ENV_DEFAULT = ROOT / "web" / ".env.local"
WEB_ENV_EXAMPLE = ROOT / "web" / ".env.local.example"
ROOT_ENV = ROOT_ENV_DEFAULT
WEB_ENV = WEB_ENV_DEFAULT
ACTIVE_PROFILE = "default"


CATALOG: list[ConfigVar] = [
    ConfigVar(
        "MYSQL_ROOT_PASSWORD",
        "root",
        True,
        "MariaDB root password for local Docker database management.",
        "Create your own strong password. For local dev, generate with a password manager.",
        "change_me_root_password",
        True,
    ),
    ConfigVar(
        "MYSQL_DATABASE",
        "root",
        True,
        "Default WordPress database name.",
        "Usually keep as 'wordpress' unless you changed docker compose/database config.",
        "wordpress",
    ),
    ConfigVar(
        "MYSQL_USER",
        "root",
        True,
        "Application database username used by WordPress.",
        "Usually keep as 'wpuser' unless you changed database config.",
        "wpuser",
    ),
    ConfigVar(
        "MYSQL_PASSWORD",
        "root",
        True,
        "Password for MYSQL_USER.",
        "Create your own strong password. Must match WordPress DB credentials.",
        "change_me_wp_password",
        True,
    ),
    ConfigVar(
        "WP_ADMIN_USER",
        "root",
        True,
        "Bootstrap WordPress admin username.",
        "Choose during setup (example: admin).",
        "admin",
    ),
    ConfigVar(
        "WP_ADMIN_PASS",
        "root",
        True,
        "Bootstrap WordPress admin password.",
        "Choose a strong password. Used for initial wp-admin login.",
        "change_me_admin_password",
        True,
    ),
    ConfigVar(
        "WP_APP_PASSWORD",
        "root",
        True,
        "WordPress Application Password used by server-side integrations.",
        "WordPress Admin -> Users -> Profile -> Application Passwords -> Add New.",
        "",
        True,
    ),
    ConfigVar(
        "DEFAULT_WP_NAME",
        "root",
        True,
        "Display name for the default auto-created WordPress connection.",
        "Any descriptive label (example: Local WordPress).",
        "Local WordPress",
    ),
    ConfigVar(
        "DEFAULT_WP_URL",
        "root",
        True,
        "Base URL for default WordPress instance.",
        "Local Docker default is http://localhost:8080.",
        "http://localhost:8080",
    ),
    ConfigVar(
        "DEFAULT_WP_GRAPHQL_ENDPOINT",
        "root",
        True,
        "WPGraphQL endpoint URL.",
        "Usually <wordpress-url>/graphql, e.g. http://localhost:8080/graphql.",
        "http://localhost:8080/graphql",
    ),
    ConfigVar(
        "DEFAULT_WP_USER",
        "root",
        True,
        "WordPress username used with DEFAULT_WP_APP_PASSWORD.",
        "Use the same account that generated the Application Password.",
        "admin",
    ),
    ConfigVar(
        "DEFAULT_WP_APP_PASSWORD",
        "root",
        True,
        "Application Password for DEFAULT_WP_USER.",
        "WordPress Admin -> Users -> Profile -> Application Passwords.",
        "${WP_APP_PASSWORD}",
        True,
    ),
    ConfigVar(
        "ENCRYPTION_KEY",
        "root",
        True,
        "Fernet-compatible key for encrypting stored credentials.",
        "Generate with command: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
        "",
        True,
    ),
    ConfigVar(
        "DOMAIN",
        "root",
        False,
        "Primary production domain (used by deployment scripts/reverse proxy).",
        "Your public DNS name, e.g. example.com.",
        "",
    ),
    ConfigVar(
        "WP_DOMAIN",
        "root",
        False,
        "Public WordPress URL/domain for production routing.",
        "Example: https://example.com",
        "",
    ),
    ConfigVar(
        "LETSENCRYPT_EMAIL",
        "root",
        False,
        "Contact email for ACME certificate registration.",
        "Use an email you control for TLS expiry notices.",
        "",
    ),
    ConfigVar(
        "TRAEFIK_AUTH",
        "root",
        False,
        "Basic auth hash for Traefik dashboard.",
        "Generate with: htpasswd -nb <user> <password>",
        "",
        True,
    ),
    ConfigVar(
        "CLOUDFLARE_API_TOKEN",
        "root",
        False,
        "Cloudflare API token for Wrangler deployments and API operations.",
        "Cloudflare Dashboard -> My Profile -> API Tokens (create token with Workers/Pages + account permissions).",
        "",
        True,
    ),
    ConfigVar(
        "CLOUDFLARE_ACCOUNT_ID",
        "root",
        False,
        "Cloudflare account ID used by Wrangler.",
        "Cloudflare Dashboard right sidebar or Workers & Pages account settings.",
        "",
    ),
    ConfigVar(
        "CLOUDFLARE_ZONE_ID",
        "root",
        False,
        "Cloudflare DNS zone ID (optional, needed for some DNS/domain operations).",
        "Cloudflare Dashboard -> Domain Overview -> API section.",
        "",
    ),
    ConfigVar(
        "WRANGLER_ENV",
        "root",
        False,
        "Named Wrangler environment for deploy commands (e.g. production, staging).",
        "Choose your deployment environment naming convention.",
        "production",
    ),
    ConfigVar(
        "ANTHROPIC_API_KEY",
        "web",
        False,
        "Anthropic API key used by Next.js server routes when BYOK is not provided.",
        "Anthropic Console -> API Keys.",
        "",
        True,
    ),
    ConfigVar(
        "MCP_SERVER_URL",
        "web",
        True,
        "URL where Next.js server reaches MCP server.",
        "Local default: http://localhost:8000 (or internal service URL in production).",
        "http://localhost:8000",
    ),
    ConfigVar(
        "DEFAULT_WP_NAME",
        "web",
        True,
        "Display name for web-side default WordPress connection values.",
        "Keep aligned with root DEFAULT_WP_NAME.",
        "Local WordPress",
    ),
    ConfigVar(
        "DEFAULT_WP_URL",
        "web",
        True,
        "WordPress URL used by web backend defaults.",
        "Keep aligned with root DEFAULT_WP_URL.",
        "http://localhost:8080",
    ),
    ConfigVar(
        "DEFAULT_WP_GRAPHQL_ENDPOINT",
        "web",
        True,
        "GraphQL endpoint used by web backend defaults.",
        "Keep aligned with root DEFAULT_WP_GRAPHQL_ENDPOINT.",
        "http://localhost:8080/graphql",
    ),
    ConfigVar(
        "DEFAULT_WP_USER",
        "web",
        True,
        "WordPress user for default web-side connection.",
        "Keep aligned with root DEFAULT_WP_USER.",
        "admin",
    ),
    ConfigVar(
        "DEFAULT_WP_APP_PASSWORD",
        "web",
        True,
        "WordPress Application Password for web-side default connection.",
        "WordPress Admin -> Users -> Profile -> Application Passwords.",
        "",
        True,
    ),
]


class Colors:
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def profile_paths(profile: str) -> tuple[Path, Path]:
    p = profile.strip()
    if p in {"", "default"}:
        return ROOT_ENV_DEFAULT, WEB_ENV_DEFAULT
    return ROOT / f".env.{p}", ROOT / "web" / f".env.{p}.local"


def set_active_profile(profile: str) -> None:
    global ROOT_ENV, WEB_ENV, ACTIVE_PROFILE
    root_env, web_env = profile_paths(profile)
    ROOT_ENV = root_env
    WEB_ENV = web_env
    ACTIVE_PROFILE = profile or "default"


def _is_valid_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_var(var: ConfigVar, value: str) -> list[str]:
    errors: list[str] = []
    v = value.strip()
    if var.required and not v:
        errors.append(f"{var.name}@{var.target}: required but empty")
        return errors
    if not v:
        return errors

    if any(x in var.name for x in ["URL", "ENDPOINT"]) and not _is_valid_http_url(v):
        errors.append(f"{var.name}@{var.target}: must be a valid http/https URL")
    if var.name.endswith("GRAPHQL_ENDPOINT") and "/graphql" not in v:
        errors.append(f"{var.name}@{var.target}: should include '/graphql'")
    if var.name == "LETSENCRYPT_EMAIL" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
        errors.append(f"{var.name}@{var.target}: must be a valid email")
    if var.name == "ENCRYPTION_KEY":
        try:
            decoded = base64.urlsafe_b64decode(v.encode())
            if len(decoded) != 32:
                errors.append(f"{var.name}@{var.target}: must decode to 32 bytes (Fernet key)")
        except Exception:
            errors.append(f"{var.name}@{var.target}: invalid urlsafe base64 key")
    if var.name in {"CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_ZONE_ID"} and not re.match(r"^[a-fA-F0-9]{32}$", v):
        errors.append(f"{var.name}@{var.target}: should be 32 hex chars")
    if var.name == "WRANGLER_ENV" and not re.match(r"^[A-Za-z0-9_-]+$", v):
        errors.append(f"{var.name}@{var.target}: only letters, numbers, '_' and '-' are allowed")
    if var.name in {"WP_ADMIN_PASS", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"} and len(v) < 8:
        errors.append(f"{var.name}@{var.target}: should be at least 8 characters")
    if var.name == "MCP_SERVER_URL" and not _is_valid_http_url(v):
        errors.append(f"{var.name}@{var.target}: must be a valid URL to MCP server")

    return errors


def validate_all(values: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for var in CATALOG:
        value = values[var.target].get(var.name, "")
        errors.extend(validate_var(var, value))
    return errors


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def mask(value: str, is_secret: bool) -> str:
    if not value:
        return "(empty)"
    if not is_secret:
        return value
    if len(value) <= 6:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def ensure_file(path: Path, fallback_example: Path | None = None) -> None:
    if path.exists():
        return
    if fallback_example and fallback_example.exists():
        path.write_text(fallback_example.read_text())
        return
    path.write_text("")


def write_env(path: Path, target: str, values: dict[str, str]) -> None:
    ensure_file(path)
    keys_in_target = {v.name for v in CATALOG if v.target == target}
    preserved = parse_env(path)
    unknown = {k: v for k, v in preserved.items() if k not in keys_in_target}

    lines: list[str] = []
    lines.append("# Generated by scripts/configure_project.py")
    lines.append(f"# Target: {target}")
    lines.append("")
    for var in [v for v in CATALOG if v.target == target]:
        lines.append(f"# {var.description}")
        lines.append(f"# Where: {var.where_to_find}")
        lines.append(f"{var.name}={values.get(var.name, var.default)}")
        lines.append("")

    if unknown:
        lines.append("# Preserved keys not managed by configure_project.py")
        for key in sorted(unknown):
            lines.append(f"{key}={unknown[key]}")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n")


def split_key_ref(key_ref: str) -> tuple[str, str | None]:
    if "@" not in key_ref:
        return key_ref.strip(), None
    key, target = key_ref.split("@", 1)
    t = target.strip().lower()
    if t not in {"root", "web"}:
        raise ValueError("target must be root or web (use KEY@root or KEY@web)")
    return key.strip(), t


def matching_vars(key: str, target: str | None) -> list[ConfigVar]:
    return [v for v in CATALOG if v.name == key and (target is None or v.target == target)]


def print_intro() -> None:
    print(
        f"{Colors.PURPLE}{Colors.BOLD}"
        "██████╗  █████╗  ██████╗ ██████╗  █████╗ ███████╗\n"
        "██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔══██╗╚══███╔╝\n"
        "██████╔╝███████║██║  ███╗██████╔╝███████║  ███╔╝ \n"
        "██╔══██╗██╔══██║██║   ██║██╔══██╗██╔══██║ ███╔╝  \n"
        "██║  ██║██║  ██║╚██████╔╝██████╔╝██║  ██║███████╗\n"
        "╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
        f"{Colors.RESET}"
    )
    print(f"{Colors.CYAN}WP-AI Project Configuration Menu{Colors.RESET}")
    print(f"{Colors.CYAN}Active profile: {ACTIVE_PROFILE}{Colors.RESET}\n")
    print("Managed files:")
    print(f"  1) {ROOT_ENV}")
    print(f"  2) {WEB_ENV}")
    print("")
    print("Select options by number. This tool explains each key, what it means, and where to obtain it.\n")


def print_list(values: dict[str, dict[str, str]], mode: str) -> None:
    for var in CATALOG:
        current = values[var.target].get(var.name, "")
        missing = var.required and not current
        if mode == "required" and not var.required:
            continue
        if mode == "missing" and not missing:
            continue
        print(
            f"{Colors.CYAN}{var.name}@{var.target:<4}{Colors.RESET} "
            f"required={'yes' if var.required else 'no ':<3} "
            f"value={mask(current, var.secret)}"
        )


def print_info(var: ConfigVar, values: dict[str, dict[str, str]]) -> None:
    current = values[var.target].get(var.name, "")
    print(f"{Colors.BOLD}{var.name}@{var.target}{Colors.RESET}")
    print(f"Meaning: {var.description}")
    print(f"Where:   {var.where_to_find}")
    print(f"Required:{' yes' if var.required else ' no'}")
    print(f"Current: {mask(current, var.secret)}")
    if var.default:
        print(f"Default: {var.default}")


def status(values: dict[str, dict[str, str]]) -> int:
    missing: list[str] = []
    for var in CATALOG:
        if var.required and not values[var.target].get(var.name, ""):
            missing.append(f"{var.name}@{var.target}")
    if not missing:
        print(f"{Colors.GREEN}All required variables are set.{Colors.RESET}")
        return 0
    print(f"{Colors.YELLOW}Missing required variables:{Colors.RESET}")
    for item in missing:
        print(f"- {item}")
    return 1


def prompt_for(var: ConfigVar, values: dict[str, dict[str, str]]) -> None:
    print_info(var, values)
    entered = input(f"Enter value for {var.name}@{var.target} (empty to keep current): ").strip()
    if entered:
        values[var.target][var.name] = entered
        print(f"{Colors.GREEN}Updated {var.name}@{var.target}{Colors.RESET}")


def generate_fernet_like_key() -> str:
    # Fernet keys are URL-safe base64-encoded 32-byte values.
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def clear_screen() -> None:
    print("\033c", end="")


def choose_var() -> ConfigVar | None:
    print("Enter variable as KEY or KEY@root or KEY@web")
    key_ref = input("Variable: ").strip()
    if not key_ref:
        return None
    try:
        key, target = split_key_ref(key_ref)
    except ValueError as e:
        print(f"{Colors.RED}{e}{Colors.RESET}")
        return None
    matches = matching_vars(key, target)
    if not matches:
        print(f"{Colors.RED}Unknown key.{Colors.RESET}")
        return None
    if len(matches) > 1 and target is None:
        print(f"{Colors.YELLOW}Ambiguous key. Use @root or @web.{Colors.RESET}")
        return None
    return matches[0]


def set_var_menu(values: dict[str, dict[str, str]]) -> None:
    var = choose_var()
    if not var:
        return
    print_info(var, values)
    value = input(f"New value for {var.name}@{var.target}: ").strip()
    if value == "":
        print("No change.")
        return
    values[var.target][var.name] = value
    print(f"{Colors.GREEN}Updated {var.name}@{var.target}{Colors.RESET}")


def wizard(values: dict[str, dict[str, str]], required_only: bool) -> None:
    vars_to_prompt = [v for v in CATALOG if (v.required if required_only else True)]
    for var in vars_to_prompt:
        prompt_for(var, values)


def list_menu(values: dict[str, dict[str, str]]) -> None:
    print("1) all")
    print("2) required")
    print("3) missing")
    choice = input("Mode: ").strip()
    mapping = {"1": "all", "2": "required", "3": "missing"}
    mode = mapping.get(choice)
    if not mode:
        print("Invalid mode.")
        return
    print_list(values, mode)


def switch_profile(values: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    profile = input("Profile name [default|dev|staging|prod|custom]: ").strip() or "default"
    set_active_profile(profile)
    ensure_file(ROOT_ENV, ROOT_ENV_EXAMPLE)
    ensure_file(WEB_ENV, WEB_ENV_EXAMPLE)
    print(f"{Colors.GREEN}Switched to profile: {ACTIVE_PROFILE}{Colors.RESET}")
    return {
        "root": parse_env(ROOT_ENV),
        "web": parse_env(WEB_ENV),
    }


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    shown = " ".join(cmd)
    where = str(cwd or ROOT)
    print(f"{Colors.CYAN}Running:{Colors.RESET} {shown}")
    print(f"{Colors.CYAN}In:{Colors.RESET} {where}")
    try:
        result = subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, check=False)
    except FileNotFoundError:
        print(f"{Colors.RED}Command not found: {cmd[0]}{Colors.RESET}")
        return 127
    if result.returncode == 0:
        print(f"{Colors.GREEN}Command completed successfully.{Colors.RESET}")
    else:
        print(f"{Colors.RED}Command failed with exit code {result.returncode}.{Colors.RESET}")
    return result.returncode


def has_cmd(name: str) -> bool:
    result = subprocess.run(["bash", "-lc", f"command -v {name} >/dev/null 2>&1"], check=False)
    return result.returncode == 0


def docker_ready() -> bool:
    if not has_cmd("docker"):
        return False
    result = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def preflight(action: str) -> bool:
    required: list[str] = []
    if action in {"build-web", "dev-web"}:
        required.extend(["npm"])
    if action in {"build-docker", "start-local", "deploy-prod"}:
        required.extend(["docker"])
    if action.startswith("wrangler"):
        required.extend(["wrangler"])

    missing = [c for c in required if not has_cmd(c)]
    if missing:
        print(f"{Colors.RED}Missing required commands: {', '.join(missing)}{Colors.RESET}")
        return False
    if action in {"build-docker", "start-local", "deploy-prod"} and not docker_ready():
        print(f"{Colors.RED}Docker daemon is not ready. Start Docker and retry.{Colors.RESET}")
        return False
    return True


def validate_runtime_location() -> int:
    """Ensure tool is run from project root or scripts/ directory."""
    cwd = Path.cwd().resolve()
    allowed = {ROOT.resolve(), (ROOT / "scripts").resolve()}
    if cwd not in allowed:
        print(f"{Colors.RED}Invalid working directory: {cwd}{Colors.RESET}")
        print("Run this tool from one of:")
        print(f"  - {ROOT}")
        print(f"  - {ROOT / 'scripts'}")
        print("Examples:")
        print("  python3 scripts/configure_project.py")
        print("  cd scripts && python3 configure_project.py")
        return 1
    # Normalize all relative command execution to project root.
    os.chdir(ROOT)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WP-AI project configurator")
    parser.add_argument("--profile", default="default", help="Config profile (default/dev/staging/prod/custom)")
    parser.add_argument("--set", dest="sets", action="append", default=[], help="Set key as KEY=VALUE or KEY@target=VALUE")
    parser.add_argument("--save", action="store_true", help="Save after applying --set")
    parser.add_argument("--status", action="store_true", help="Print missing required values")
    parser.add_argument("--validate", action="store_true", help="Run validation and exit non-zero on errors")
    parser.add_argument(
        "--run",
        choices=[
            "build-web",
            "build-docker",
            "start-local",
            "deploy-prod",
            "dev-web",
            "wrangler-login",
            "wrangler-whoami",
            "wrangler-dev",
            "wrangler-deploy",
            "wrangler-pages-deploy",
        ],
        help="Run one operation in non-interactive mode",
    )
    parser.add_argument("--project-dir", default="", help="Project dir override for wrangler operations")
    parser.add_argument("--pages-project", default="", help="Cloudflare Pages project name")
    parser.add_argument("--pages-output", default="dist", help="Cloudflare Pages output directory")
    return parser.parse_args()


def apply_set(values: dict[str, dict[str, str]], item: str) -> None:
    if "=" not in item:
        raise ValueError(f"Invalid --set value '{item}'. Expected KEY=VALUE")
    key_ref, value = item.split("=", 1)
    key, target = split_key_ref(key_ref)
    matches = matching_vars(key, target)
    if not matches:
        raise ValueError(f"Unknown key in --set: {key_ref}")
    if len(matches) > 1 and target is None:
        raise ValueError(f"Ambiguous key in --set: {key_ref}. Use @root or @web")
    var = matches[0]
    values[var.target][var.name] = value


def run_noninteractive(args: argparse.Namespace, values: dict[str, dict[str, str]]) -> int:
    for item in args.sets:
        apply_set(values, item)

    if args.validate:
        errors = validate_all(values)
        if errors:
            print(f"{Colors.RED}Validation errors:{Colors.RESET}")
            for err in errors:
                print(f"- {err}")
            return 1
        print(f"{Colors.GREEN}Validation passed.{Colors.RESET}")

    if args.status:
        missing_rc = status(values)
        if missing_rc != 0:
            return missing_rc

    if args.save:
        errors = validate_all(values)
        if errors:
            print(f"{Colors.RED}Cannot save due to validation errors:{Colors.RESET}")
            for err in errors:
                print(f"- {err}")
            return 1
        write_env(ROOT_ENV, "root", values["root"])
        write_env(WEB_ENV, "web", values["web"])
        print(f"{Colors.GREEN}Saved:{Colors.RESET} {ROOT_ENV}")
        print(f"{Colors.GREEN}Saved:{Colors.RESET} {WEB_ENV}")

    if args.run:
        op_env = dict(os.environ)
        op_env.update(values.get("root", {}))
        op_env.update(values.get("web", {}))
        if not preflight(args.run):
            return 1
        if args.run == "build-web":
            return run_cmd(["npm", "run", "build"], cwd=ROOT / "web", env=op_env)
        if args.run == "build-docker":
            return run_cmd(["docker", "compose", "build"], cwd=ROOT, env=op_env)
        if args.run == "start-local":
            return run_cmd(["docker", "compose", "up", "-d"], cwd=ROOT, env=op_env)
        if args.run == "deploy-prod":
            return run_cmd(
                ["docker", "compose", "-f", "docker-compose.production.yml", "up", "-d", "--build"],
                cwd=ROOT,
                env=op_env,
            )
        if args.run == "dev-web":
            return run_cmd(["npm", "run", "dev"], cwd=ROOT / "web", env=op_env)

        project_dir = Path(args.project_dir) if args.project_dir else choose_wrangler_project_dir()
        if args.run == "wrangler-login":
            return run_cmd(["wrangler", "login"], cwd=project_dir, env=op_env)
        if args.run == "wrangler-whoami":
            return run_cmd(["wrangler", "whoami"], cwd=project_dir, env=op_env)
        if args.run == "wrangler-dev":
            return run_cmd(["wrangler", "dev"], cwd=project_dir, env=op_env)
        if args.run == "wrangler-deploy":
            cmd = ["wrangler", "deploy"]
            wrangler_env = (values.get("root", {}).get("WRANGLER_ENV") or "").strip()
            if wrangler_env:
                cmd.extend(["--env", wrangler_env])
            return run_cmd(cmd, cwd=project_dir, env=op_env)
        if args.run == "wrangler-pages-deploy":
            if not args.pages_project:
                print(f"{Colors.RED}--pages-project is required for wrangler-pages-deploy{Colors.RESET}")
                return 1
            return run_cmd(
                ["wrangler", "pages", "deploy", args.pages_output, "--project-name", args.pages_project],
                cwd=project_dir,
                env=op_env,
            )
    return 0


def find_wrangler_projects() -> list[Path]:
    """Find project directories containing wrangler.toml (prefers shallow paths)."""
    matches = sorted(ROOT.glob("**/wrangler.toml"), key=lambda p: len(p.parts))
    dirs: list[Path] = []
    for match in matches:
        parent = match.parent
        if parent not in dirs:
            dirs.append(parent)
    return dirs


def choose_wrangler_project_dir() -> Path:
    projects = find_wrangler_projects()
    if not projects:
        return ROOT / "web"
    if len(projects) == 1:
        return projects[0]

    print(f"{Colors.CYAN}Multiple wrangler projects detected:{Colors.RESET}")
    for idx, project in enumerate(projects, start=1):
        print(f"  {idx}) {project}")
    selected = input(f"Select project [1]: ").strip()
    if not selected:
        return projects[0]
    try:
        n = int(selected)
        if 1 <= n <= len(projects):
            return projects[n - 1]
    except ValueError:
        pass
    print(f"{Colors.YELLOW}Invalid selection, using first project.{Colors.RESET}")
    return projects[0]


def operations_menu(values: dict[str, dict[str, str]]) -> None:
    print(f"{Colors.BOLD}Operations Menu{Colors.RESET}")
    print("  1) Build web app (npm run build)")
    print("  2) Build Docker services (docker compose build)")
    print("  3) Start local stack (docker compose up -d)")
    print("  4) Deploy production stack (docker compose -f docker-compose.production.yml up -d --build)")
    print("  5) Run web development server (npm run dev)")
    print("  6) Cloudflare/Wrangler menu")
    print("  7) Back")
    choice = input("Select: ").strip()

    # Use currently edited values for process env (even before save).
    op_env = dict(os.environ)
    op_env.update(values.get("root", {}))
    op_env.update(values.get("web", {}))

    if choice == "1":
        if confirm("Build Next.js web app now?") and preflight("build-web"):
            run_cmd(["npm", "run", "build"], cwd=ROOT / "web", env=op_env)
    elif choice == "2":
        if confirm("Build all Docker services now?") and preflight("build-docker"):
            run_cmd(["docker", "compose", "build"], cwd=ROOT, env=op_env)
    elif choice == "3":
        if confirm("Start local stack in detached mode now?") and preflight("start-local"):
            run_cmd(["docker", "compose", "up", "-d"], cwd=ROOT, env=op_env)
    elif choice == "4":
        if confirm("Deploy production stack now (detached, with build)?") and preflight("deploy-prod"):
            run_cmd(
                ["docker", "compose", "-f", "docker-compose.production.yml", "up", "-d", "--build"],
                cwd=ROOT,
                env=op_env,
            )
    elif choice == "5":
        print(
            f"{Colors.YELLOW}This runs in foreground. Stop with Ctrl+C to return to the menu.{Colors.RESET}"
        )
        if confirm("Start web development server now?") and preflight("dev-web"):
            run_cmd(["npm", "run", "dev"], cwd=ROOT / "web", env=op_env)
    elif choice == "6":
        wrangler_menu(values)
    elif choice == "7":
        return
    else:
        print(f"{Colors.RED}Invalid option.{Colors.RESET}")


def wrangler_menu(values: dict[str, dict[str, str]]) -> None:
    print(f"{Colors.BOLD}Cloudflare/Wrangler Menu{Colors.RESET}")
    print("  1) wrangler login")
    print("  2) wrangler whoami")
    print("  3) wrangler dev")
    print("  4) wrangler deploy")
    print("  5) wrangler pages deploy")
    print("  6) Back")
    choice = input("Select: ").strip()

    op_env = dict(os.environ)
    op_env.update(values.get("root", {}))
    op_env.update(values.get("web", {}))

    # Auto-detect wrangler.toml projects; fallback to web directory.
    default_dir = choose_wrangler_project_dir()
    if (default_dir / "wrangler.toml").exists():
        print(f"{Colors.GREEN}Detected wrangler project:{Colors.RESET} {default_dir}")
    else:
        print(
            f"{Colors.YELLOW}No wrangler.toml detected; using fallback directory:{Colors.RESET} {default_dir}"
        )
    dir_raw = input(f"Project directory [{default_dir}]: ").strip()
    project_dir = Path(dir_raw) if dir_raw else default_dir

    if choice == "1":
        if confirm("Run 'wrangler login' now?") and preflight("wrangler-login"):
            run_cmd(["wrangler", "login"], cwd=project_dir, env=op_env)
    elif choice == "2":
        if confirm("Run 'wrangler whoami' now?") and preflight("wrangler-whoami"):
            run_cmd(["wrangler", "whoami"], cwd=project_dir, env=op_env)
    elif choice == "3":
        if confirm("Run 'wrangler dev' now?") and preflight("wrangler-dev"):
            run_cmd(["wrangler", "dev"], cwd=project_dir, env=op_env)
    elif choice == "4":
        wrangler_env = (values.get("root", {}).get("WRANGLER_ENV") or "").strip()
        cmd = ["wrangler", "deploy"]
        if wrangler_env:
            cmd.extend(["--env", wrangler_env])
        if confirm(f"Run '{' '.join(cmd)}' now?") and preflight("wrangler-deploy"):
            run_cmd(cmd, cwd=project_dir, env=op_env)
    elif choice == "5":
        build_dir = input("Pages build output directory [dist]: ").strip() or "dist"
        project_name = input("Cloudflare Pages project name: ").strip()
        if not project_name:
            print(f"{Colors.RED}Project name is required for pages deploy.{Colors.RESET}")
            return
        cmd = ["wrangler", "pages", "deploy", build_dir, "--project-name", project_name]
        if confirm(f"Run '{' '.join(cmd)}' now?") and preflight("wrangler-pages-deploy"):
            run_cmd(cmd, cwd=project_dir, env=op_env)
    elif choice == "6":
        return
    else:
        print(f"{Colors.RED}Invalid option.{Colors.RESET}")


def main() -> int:
    args = parse_args()
    rc = validate_runtime_location()
    if rc != 0:
        return rc

    set_active_profile(args.profile)
    ensure_file(ROOT_ENV, ROOT_ENV_EXAMPLE)
    ensure_file(WEB_ENV, WEB_ENV_EXAMPLE)

    values = {
        "root": parse_env(ROOT_ENV),
        "web": parse_env(WEB_ENV),
    }

    has_noninteractive = bool(args.sets or args.save or args.status or args.validate or args.run)
    if has_noninteractive:
        return run_noninteractive(args, values)

    while True:
        clear_screen()
        print_intro()
        print("Menu:")
        print("  1) Guided setup (required variables)")
        print("  2) Guided setup (all variables)")
        print("  3) List variables")
        print("  4) Show variable info")
        print("  5) Set variable value")
        print("  6) Generate ENCRYPTION_KEY")
        print("  7) Save to .env files")
        print("  8) Status (missing required)")
        print("  9) Build/Deploy/Start/Dev operations")
        print(" 10) Validate values")
        print(" 11) Switch profile")
        print(" 12) Quit")
        choice = input("\nSelect: ").strip()

        if choice == "1":
            wizard(values, required_only=True)
        elif choice == "2":
            wizard(values, required_only=False)
        elif choice == "3":
            list_menu(values)
        elif choice == "4":
            var = choose_var()
            if var:
                print_info(var, values)
        elif choice == "5":
            set_var_menu(values)
        elif choice == "6":
            values["root"]["ENCRYPTION_KEY"] = generate_fernet_like_key()
            print(f"{Colors.GREEN}Generated ENCRYPTION_KEY@root.{Colors.RESET}")
        elif choice == "7":
            errors = validate_all(values)
            if errors:
                print(f"{Colors.RED}Cannot save due to validation errors:{Colors.RESET}")
                for err in errors:
                    print(f"- {err}")
                input("\nFix values before saving. Press Enter...")
                continue
            write_env(ROOT_ENV, "root", values["root"])
            write_env(WEB_ENV, "web", values["web"])
            print(f"{Colors.GREEN}Saved:{Colors.RESET} {ROOT_ENV}")
            print(f"{Colors.GREEN}Saved:{Colors.RESET} {WEB_ENV}")
            status(values)
        elif choice == "8":
            status(values)
        elif choice == "9":
            operations_menu(values)
        elif choice == "10":
            errors = validate_all(values)
            if not errors:
                print(f"{Colors.GREEN}Validation passed.{Colors.RESET}")
            else:
                print(f"{Colors.RED}Validation errors:{Colors.RESET}")
                for err in errors:
                    print(f"- {err}")
        elif choice == "11":
            values = switch_profile(values)
        elif choice == "12":
            print("Use option 7 before quit if you want to persist changes.")
            return 0
        else:
            print(f"{Colors.RED}Invalid option.{Colors.RESET}")
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Handle cases like: script | head
        sys.exit(0)
