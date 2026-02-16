"""URL validation to prevent SSRF attacks."""

from __future__ import annotations

import ipaddress
import logging
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
            # Not an IP address, could be a domain name
            # For domain names, we can't validate without DNS resolution
            # which could be slow or unreliable. We'll allow domains but
            # log them for monitoring.
            logger.info(f"Allowing domain name URL: {parsed.hostname}")
            return True, None
        
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
