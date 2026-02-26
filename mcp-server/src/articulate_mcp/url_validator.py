"""URL validation to prevent SSRF attacks."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private IP ranges to block
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

# Metadata endpoints to block (cloud providers)
BLOCKED_HOSTS = [
    "169.254.169.254",  # AWS/Azure/GCP metadata
    "metadata.google.internal",  # GCP metadata
    "169.254.169.253",  # Alibaba Cloud
    "100.100.100.200",  # Alibaba Cloud
]


def validate_url(url: str, require_https: bool = False) -> tuple[bool, Optional[str]]:
    """Validate a URL to prevent SSRF attacks.
    
    Args:
        url: URL to validate
        require_https: If True, only allow HTTPS URLs
        
    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ["http", "https"]:
            return False, f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed."
        
        if require_https and parsed.scheme != "https":
            return False, "HTTPS is required for this URL."
        
        # Check for empty hostname
        if not parsed.hostname:
            return False, "URL must have a hostname."
        
        # Block metadata endpoints
        if parsed.hostname in BLOCKED_HOSTS:
            logger.warning(f"Blocked metadata endpoint access: {parsed.hostname}")
            return False, "Access to cloud metadata endpoints is not allowed."
        
        # Try to resolve hostname to IP
        try:
            ip = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            # Not a direct IP address, perform DNS resolution
            try:
                # Resolve domain name to IP addresses
                addr_info = socket.getaddrinfo(
                    parsed.hostname,
                    None,
                    socket.AF_UNSPEC,
                    socket.SOCK_STREAM,
                    0,
                    socket.AI_ADDRCONFIG
                )

                # Check all resolved IPs
                for family, _, _, _, sockaddr in addr_info:
                    resolved_ip_str = sockaddr[0]
                    try:
                        resolved_ip = ipaddress.ip_address(resolved_ip_str)

                        # Check if any resolved IP is in private range
                        for private_range in PRIVATE_IP_RANGES:
                            if resolved_ip in private_range:
                                logger.warning(
                                    f"Blocked domain {parsed.hostname} resolving to private IP: {resolved_ip}"
                                )
                                return False, f"Domain resolves to private IP address: {resolved_ip}"

                        # Check against blocked hosts
                        if resolved_ip_str in BLOCKED_HOSTS:
                            logger.warning(
                                f"Blocked domain {parsed.hostname} resolving to blocked IP: {resolved_ip}"
                            )
                            return False, f"Domain resolves to blocked IP address: {resolved_ip}"

                    except ValueError:
                        # Invalid IP in resolution results
                        logger.warning(f"Invalid IP in DNS resolution for {parsed.hostname}: {resolved_ip_str}")
                        continue

                # All resolved IPs are safe
                logger.debug(f"DNS validation passed for domain: {parsed.hostname}")
                return True, None

            except socket.gaierror as e:
                # DNS resolution failed
                logger.warning(f"DNS resolution failed for {parsed.hostname}: {e}")
                return False, f"Cannot resolve domain name: {parsed.hostname}"
            except socket.timeout:
                logger.warning(f"DNS resolution timeout for {parsed.hostname}")
                return False, f"DNS resolution timeout for domain: {parsed.hostname}"
            except Exception as e:
                logger.error(f"Unexpected DNS resolution error for {parsed.hostname}: {e}")
                return False, f"DNS resolution error: {str(e)}"

        # Check if IP is in private range
        for private_range in PRIVATE_IP_RANGES:
            if ip in private_range:
                logger.warning(f"Blocked private IP access: {ip}")
                return False, f"Access to private IP addresses is not allowed: {ip}"
        
        return True, None
        
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False, f"Invalid URL: {str(e)}"


def validate_wordpress_url(url: str) -> tuple[bool, Optional[str]]:
    """Validate a WordPress URL.
    
    WordPress URLs should generally be HTTPS in production but we allow HTTP
    for local development.
    
    Args:
        url: WordPress URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_url(url, require_https=False)
    
    if not is_valid:
        return False, error
    
    parsed = urlparse(url)
    
    # Allow localhost and 127.0.0.1 for development
    if parsed.hostname in ["localhost", "127.0.0.1", "::1"]:
        return True, None
    
    # Allow wordpress service name in Docker
    if parsed.hostname == "wordpress":
        return True, None
    
    # For production URLs, recommend HTTPS
    if parsed.scheme == "http" and parsed.hostname not in ["localhost", "127.0.0.1"]:
        logger.warning(f"HTTP used for non-localhost URL: {url}")
    
    return True, None
