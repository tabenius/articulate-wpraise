#!/usr/bin/env python3
"""
WP-AI Domain Configuration Tool
Interactive configuration script for setting up domains, SSL, and reverse proxy.
Supports HAProxy management, Caddy configuration, and DNS validation.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import socket


# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f"   {text}")
    print("=" * 50 + "\n")


def print_success(text: str) -> None:
    """Print success message in green."""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_error(text: str) -> None:
    """Print error message in red."""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_warning(text: str) -> None:
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")


def print_info(text: str) -> None:
    """Print info message in blue."""
    print(f"{Colors.BLUE}{text}{Colors.NC}")


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).parent.resolve()
    return script_dir.parent


def get_server_ip() -> Optional[str]:
    """Get the server's public IP address."""
    try:
        with urllib.request.urlopen('https://ifconfig.me', timeout=5) as response:
            return response.read().decode('utf-8').strip()
    except Exception:
        try:
            with urllib.request.urlopen('https://icanhazip.com', timeout=5) as response:
                return response.read().decode('utf-8').strip()
        except Exception:
            return None


def check_dns(domain: str) -> Optional[str]:
    """Check DNS resolution for a domain."""
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None


def check_domain_dns(domain: str, server_ip: str) -> None:
    """Check and display DNS status for a domain."""
    resolved_ip = check_dns(domain)

    if resolved_ip:
        print_success(f"{domain} resolves to: {resolved_ip}")

        if resolved_ip == server_ip:
            print_success(f"Points to this server ({server_ip})")
        else:
            print_warning(f"Points to {resolved_ip} but server IP is {server_ip}")
            print(f"  Update DNS A record to point to {server_ip}")
    else:
        print_warning(f"{domain} does not resolve yet")
        print(f"  Add DNS A record: {domain} → {server_ip}")


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """Update or add key-value pairs in .env file."""
    if not env_path.exists():
        print_error(f".env file not found at {env_path}")
        print("Run ./scripts/setup.sh first")
        sys.exit(1)

    # Read existing content
    lines = env_path.read_text().splitlines()
    updated_keys = set()

    # Update existing keys
    for i, line in enumerate(lines):
        for key, value in updates.items():
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                updated_keys.add(key)

    # Add new keys
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}")

    # Write back
    env_path.write_text('\n'.join(lines) + '\n')
    print_success("Updated .env with domain configuration")


def update_wordpress_urls(domain: str) -> None:
    """Update WordPress site URLs in the database."""
    print("\nUpdating WordPress site URL...")

    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            check=True
        )

        if "wp-ai-wordpress" not in result.stdout:
            print_warning("WordPress container not running. URLs will be set on next startup")
            return

        url = f"https://{domain}"

        # Update home URL
        subprocess.run(
            ["docker", "exec", "wp-ai-wordpress", "wp", "option", "update",
             "home", url, "--allow-root"],
            capture_output=True,
            check=False
        )

        # Update siteurl
        subprocess.run(
            ["docker", "exec", "wp-ai-wordpress", "wp", "option", "update",
             "siteurl", url, "--allow-root"],
            capture_output=True,
            check=False
        )

        print_success(f"WordPress URLs updated to {url}")

    except subprocess.CalledProcessError:
        print_warning("Could not update WordPress URLs (wp-cli may not be ready)")


def update_caddyfile(caddyfile_path: Path, app_domain: str, wp_domain: str) -> bool:
    """Update Caddyfile with new domain names."""
    if not caddyfile_path.exists():
        print_warning(f"Caddyfile not found at {caddyfile_path}")
        return False

    # Backup original
    backup_path = caddyfile_path.with_suffix('.backup')
    shutil.copy(caddyfile_path, backup_path)

    # Read and update
    content = caddyfile_path.read_text()

    # Replace app domain
    content = re.sub(
        r'http://app\.ragbaz\.xyz',
        f'http://{app_domain}',
        content
    )

    # Replace WordPress domain
    content = re.sub(
        r'http://my\.ragbaz\.xyz',
        f'http://{wp_domain}',
        content
    )

    caddyfile_path.write_text(content)

    print_success("Updated Caddyfile with your domains")
    print(f"  App domain: {app_domain}")
    print(f"  WordPress domain: {wp_domain}")
    print(f"  Backup saved: {backup_path}")

    return True


def get_haproxy_version() -> Optional[str]:
    """Get HAProxy version."""
    try:
        result = subprocess.run(
            ["haproxy", "-v"],
            capture_output=True,
            text=True,
            check=True
        )
        # Extract version from output like "HAProxy version 2.8.0"
        match = re.search(r'version (\d+\.\d+)', result.stdout)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def test_haproxy_config(config_path: str = "/etc/haproxy/haproxy.cfg") -> Tuple[bool, str]:
    """Test HAProxy configuration syntax."""
    try:
        result = subprocess.run(
            ["sudo", "haproxy", "-c", "-f", config_path],
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout + e.stderr
    except FileNotFoundError:
        return False, "HAProxy not installed or not in PATH"


def reload_haproxy() -> Tuple[bool, str]:
    """Reload HAProxy service."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "reload", "haproxy"],
            capture_output=True,
            text=True,
            check=True
        )
        return True, "HAProxy reloaded successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to reload HAProxy: {e.stderr}"


def update_haproxy_config(
    config_path: str,
    app_domain: str,
    wp_domain: str,
    cert_path: str,
    backup: bool = True
) -> bool:
    """Update HAProxy configuration with new domains and certificate."""
    config_file = Path(config_path)

    if not config_file.exists():
        print_error(f"HAProxy config not found at {config_path}")
        return False

    # Backup
    if backup:
        backup_path = config_file.with_suffix('.cfg.backup')
        shutil.copy(config_file, backup_path)
        print_info(f"Backup created: {backup_path}")

    # Read configuration
    content = config_file.read_text()

    # Update SSL certificate path
    content = re.sub(
        r'bind \*:443 ssl crt [^\s]+',
        f'bind *:443 ssl crt {cert_path} alpn h2,http/1.1',
        content
    )

    # Update app domain ACL
    content = re.sub(
        r'acl is_app_domain hdr\(host\) -i [^\s]+',
        f'acl is_app_domain hdr(host) -i {app_domain}',
        content
    )

    # Update WordPress domain ACL
    content = re.sub(
        r'acl is_my_domain hdr\(host\) -i [^\s]+',
        f'acl is_my_domain hdr(host) -i {wp_domain}',
        content
    )

    # Update www redirect ACLs if they exist
    content = re.sub(
        r'acl is_www_app hdr\(host\) -i www\.[^\s]+',
        f'acl is_www_app hdr(host) -i www.{app_domain}',
        content
    )
    content = re.sub(
        r'acl is_www_my hdr\(host\) -i www\.[^\s]+',
        f'acl is_www_my hdr(host) -i www.{wp_domain}',
        content
    )

    # Update redirect prefixes
    content = re.sub(
        r'redirect prefix https://app\.[^\s]+ code 301 if is_www_app',
        f'redirect prefix https://{app_domain} code 301 if is_www_app',
        content
    )
    content = re.sub(
        r'redirect prefix https://my\.[^\s]+ code 301 if is_www_my',
        f'redirect prefix https://{wp_domain} code 301 if is_www_my',
        content
    )

    # Update health check Host headers
    content = re.sub(
        r'http-check send meth GET uri /health ver HTTP/1\.1 hdr Host [^\s]+',
        f'http-check send meth GET uri /health ver HTTP/1.1 hdr Host {app_domain}',
        content
    )
    content = re.sub(
        r'http-check send meth GET uri /wp-json/ ver HTTP/1\.1 hdr Host [^\s]+',
        f'http-check send meth GET uri /wp-json/ ver HTTP/1.1 hdr Host {wp_domain}',
        content
    )

    # Write back
    config_file.write_text(content)
    print_success("Updated HAProxy configuration")

    return True


def configure_haproxy(app_domain: str, wp_domain: str, root_domain: str) -> None:
    """Configure HAProxy with domains and SSL."""
    print_header("HAProxy Configuration")

    # Check if HAProxy is installed
    version = get_haproxy_version()
    if version:
        print_info(f"HAProxy version: {version}")

        # Check version compatibility
        major_version = float(version.split('.')[0])
        if major_version < 2:
            print_warning(f"HAProxy {version} detected. Version 2.0+ recommended for http-check syntax")
            print("Consider upgrading: sudo add-apt-repository ppa:vbernat/haproxy-2.8")
    else:
        print_warning("HAProxy not installed or not accessible")
        print("Install with: sudo apt install haproxy")

    print("\nSSL Certificate Configuration:")
    print("1. Cloudflare Origin Certificate (Recommended for Cloudflare users)")
    print("2. Let's Encrypt with Certbot")
    print("3. Manual certificate")
    print("")

    ssl_choice = input("Enter choice (1-3) [1]: ").strip() or "1"

    cert_path = f"/etc/haproxy/certs/{root_domain}.pem"

    if ssl_choice == "1":
        print("\n" + Colors.GREEN + "Cloudflare Origin Certificate Setup" + Colors.NC)
        print("\n1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server")
        print("2. Click 'Create Certificate'")
        print(f"3. Add hostnames: *.{root_domain}, {root_domain}")
        print("4. Save certificate and key to server:")
        print("")
        print(f"   sudo mkdir -p /etc/haproxy/certs")
        print(f"   sudo nano /etc/haproxy/certs/{root_domain}.crt   # Paste certificate")
        print(f"   sudo nano /etc/haproxy/certs/{root_domain}.key   # Paste private key")
        print("")
        print("5. Combine for HAProxy:")
        print(f"   sudo cat /etc/haproxy/certs/{root_domain}.crt \\")
        print(f"            /etc/haproxy/certs/{root_domain}.key > \\")
        print(f"            /etc/haproxy/certs/{root_domain}.pem")
        print(f"   sudo chmod 600 /etc/haproxy/certs/{root_domain}.pem")

    elif ssl_choice == "2":
        print("\n" + Colors.GREEN + "Let's Encrypt with Certbot" + Colors.NC)
        print("")
        print("1. Install certbot: sudo apt install certbot")
        print("2. Get certificate:")
        print(f"   sudo certbot certonly --standalone -d {app_domain} -d {wp_domain}")
        print("")
        print("3. Combine for HAProxy:")
        print(f"   sudo cat /etc/letsencrypt/live/{app_domain}/fullchain.pem \\")
        print(f"            /etc/letsencrypt/live/{app_domain}/privkey.pem > \\")
        print(f"            /etc/haproxy/certs/{root_domain}.pem")
        print(f"   sudo chmod 600 /etc/haproxy/certs/{root_domain}.pem")

    else:
        print("\n" + Colors.GREEN + "Manual Certificate" + Colors.NC)
        print("")
        print("1. Obtain SSL certificate from your provider")
        print("2. Combine certificate and key:")
        print(f"   cat cert.pem key.pem > /etc/haproxy/certs/{root_domain}.pem")
        print(f"   chmod 600 /etc/haproxy/certs/{root_domain}.pem")

    print("")

    # Ask if user wants to update HAProxy config
    update_config = input("Update HAProxy configuration now? (y/N): ").strip().lower()

    if update_config == 'y':
        config_path = input("HAProxy config path [/etc/haproxy/haproxy.cfg]: ").strip()
        config_path = config_path or "/etc/haproxy/haproxy.cfg"

        if update_haproxy_config(config_path, app_domain, wp_domain, cert_path):
            # Test configuration
            print("\nTesting HAProxy configuration...")
            success, output = test_haproxy_config(config_path)

            if success:
                print_success("HAProxy configuration is valid")
                print(output)

                # Ask to reload
                reload_now = input("\nReload HAProxy now? (y/N): ").strip().lower()
                if reload_now == 'y':
                    success, message = reload_haproxy()
                    if success:
                        print_success(message)
                    else:
                        print_error(message)
                else:
                    print_info("Reload HAProxy later with: sudo systemctl reload haproxy")
            else:
                print_error("HAProxy configuration test failed:")
                print(output)
                print("\nConfiguration has been updated but not reloaded.")
                print("Fix the errors and test with: sudo haproxy -c -f " + config_path)

    print("\n" + Colors.YELLOW + "Important:" + Colors.NC)
    print("  - See HAPROXY_CONFIG.md for complete configuration reference")
    print("  - See CLOUDFLARE_SETUP.md for DNS and security settings")
    print(f"  - Certificate path: {cert_path}")


def main():
    """Main configuration flow."""
    parser = argparse.ArgumentParser(description='WP-AI Domain Configuration Tool')
    parser.add_argument('--app-domain', help='Application domain (e.g., app.example.com)')
    parser.add_argument('--wp-domain', help='WordPress domain (e.g., my.example.com)')
    parser.add_argument('--haproxy', action='store_true', help='Use HAProxy mode')
    parser.add_argument('--haproxy-config', help='Path to HAProxy config file')
    parser.add_argument('--test-haproxy', action='store_true', help='Test HAProxy config and exit')
    parser.add_argument('--reload-haproxy', action='store_true', help='Reload HAProxy and exit')

    args = parser.parse_args()

    # Handle quick actions
    if args.test_haproxy:
        config_path = args.haproxy_config or "/etc/haproxy/haproxy.cfg"
        success, output = test_haproxy_config(config_path)
        print(output)
        sys.exit(0 if success else 1)

    if args.reload_haproxy:
        success, message = reload_haproxy()
        print(message)
        sys.exit(0 if success else 1)

    # Interactive configuration
    project_root = get_project_root()
    os.chdir(project_root)

    print_header("WP-AI Domain Configuration Tool")
    print(f"Project root: {project_root}\n")

    # Determine proxy type
    if args.haproxy:
        use_haproxy = True
    else:
        print("Which reverse proxy are you using?\n")
        print("1. HAProxy (SSL termination + Caddy for HTTP routing)")
        print("2. Direct Caddy (Caddy handles SSL and routing)")
        print("3. Nginx, Traefik, or other\n")

        choice = input("Enter choice (1-3) [1]: ").strip() or "1"
        use_haproxy = choice == "1"

    print("")

    if use_haproxy:
        print_info("HAProxy mode selected")
        print("\nThis setup uses:")
        print("  - HAProxy: SSL termination, domain routing (port 443)")
        print("  - Caddy: HTTP reverse proxy (port 4555)")
        print("  - Split domains: App domain + WordPress domain\n")

        # Get domains
        app_domain = args.app_domain or input("Enter your app domain (e.g., app.example.com): ").strip()
        if not app_domain:
            print_error("App domain cannot be empty")
            sys.exit(1)

        wp_domain = args.wp_domain or input("Enter your WordPress domain (e.g., my.example.com): ").strip()
        if not wp_domain:
            print_error("WordPress domain cannot be empty")
            sys.exit(1)

        # Extract root domain (e.g., example.com from app.example.com)
        root_domain = '.'.join(app_domain.split('.')[-2:])

        print("")
        print_info(f"App Domain: {app_domain}")
        print_info(f"WordPress Domain: {wp_domain}")
        print("")

        # Check DNS
        print("Checking DNS resolution...")
        server_ip = get_server_ip()

        if server_ip:
            print(f"Server IP: {server_ip}\n")
            print("Checking app domain...")
            check_domain_dns(app_domain, server_ip)
            print("\nChecking WordPress domain...")
            check_domain_dns(wp_domain, server_ip)
        else:
            print_warning("Could not determine server IP")

        print("")

        # Update .env
        print("Updating .env configuration...")
        env_path = project_root / '.env'
        update_env_file(env_path, {
            'DOMAIN': app_domain,
            'WP_DOMAIN': f'https://{wp_domain}',
            'APP_DOMAIN': app_domain,
            'WP_SUBDOMAIN': wp_domain
        })

        # Update Caddyfile
        print("\nUpdating Caddyfile...")
        caddyfile_path = project_root / 'docker' / 'caddy' / 'Caddyfile'
        update_caddyfile(caddyfile_path, app_domain, wp_domain)

        # Update WordPress URLs
        update_wordpress_urls(wp_domain)

        # Configure HAProxy
        configure_haproxy(app_domain, wp_domain, root_domain)

        # Next steps
        print_header("Next Steps")
        print("HAProxy + Caddy Split-Domain Setup:\n")
        print("1. DNS Configuration (Cloudflare recommended):")
        print(f"   • A record: {app_domain} → {server_ip} (Proxied)")
        print(f"   • A record: {wp_domain} → {server_ip} (Proxied)")
        print("   See CLOUDFLARE_SETUP.md for complete DNS and security settings\n")
        print("2. Restart Docker services:")
        print("   docker compose down")
        print("   docker compose build caddy")
        print("   docker compose up -d\n")
        print("3. Test your setup:")
        print(f"   • App: https://{app_domain}")
        print(f"   • WordPress: https://{wp_domain}")
        print(f"   • WordPress Admin: https://{wp_domain}/wp-admin\n")
        print("Architecture:")
        print("  Internet → Cloudflare → HAProxy:443 (SSL) → Caddy:4555 (HTTP)")
        print(f"    ├─ {app_domain} → web:3000 (Next.js)")
        print(f"    └─ {wp_domain} → wordpress:80")

    else:
        # Single domain configuration
        domain = input("Enter your domain name (e.g., example.com): ").strip()
        if not domain:
            print_error("Domain cannot be empty")
            sys.exit(1)

        print("")
        print_info(f"Domain: {domain}")
        print("")

        # Check DNS
        print("Checking DNS resolution...")
        server_ip = get_server_ip()

        if server_ip:
            check_domain_dns(domain, server_ip)

        print("")

        # Update .env
        print("Updating .env configuration...")
        env_path = project_root / '.env'
        update_env_file(env_path, {
            'DOMAIN': domain,
            'WP_DOMAIN': f'https://{domain}'
        })

        # Update WordPress URLs
        update_wordpress_urls(domain)

        # Next steps
        print_header("Next Steps")
        print("1. Ensure DNS points to this server")
        print("2. Set up SSL certificate")
        print("3. Configure reverse proxy (see docker/caddy/Caddyfile)")
        print("4. Restart services: docker compose -f docker-compose.production.yml up -d")
        print(f"5. Test: https://{domain}")

    print("")
    print_success("Configuration complete!")
    print("\nFor help, see:")
    print("  • HAPROXY_CONFIG.md - Complete HAProxy setup")
    print("  • CLOUDFLARE_SETUP.md - DNS and security settings")
    print("  • docker/caddy/Caddyfile - Caddy configuration")
    print("")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(1)
