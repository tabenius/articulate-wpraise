#!/usr/bin/python


tenants = ["ragbaz.xyz", "survivors.se"]
key = b's4lta&peppra_nyckelbarnbarnsbarntrollungar'

import os

# ~15 tenants
#Single machine
#Shared proxy_net
#Shared control_net
#Private per-tenant network
#Persistent volumes
#Resource limits
#Security hardening
#Ready for Caddy reverse proxy
#Safe defaults for production


# core stack attach to these
template_global = """
docker network create proxy_net
docker network create control_net
"""

from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape
env = Environment(
    loader = FileSystemLoader("templates"), # PackageLoader("kasern"),
    autoescape=select_autoescape()
)
TEMPLATE = "docker-compose-tenant.yml"
template = env.get_template(TEMPLATE)

from hashlib import blake2b
h = blake2b(key=key, digest_size=16)

for t in tenants:
    h.update(t.encode("utf-8"))
    hazz = h.hexdigest()
    print(hazz)
    ID = hazz
    h.update(ID.encode("utf-8"))
    hazz = h.hexdigest()
    DB_PASSWORD = hazz
    h.update(DB_PASSWORD.encode("utf-8"))
    hazz = h.hexdigest()
    DB_ROOT_PASSWORD = hazz

    h.update(hazz.encode("utf-8"))
    hazz = h.hexdigits()
    WEBHOOK_SECRET = hazz

    container_name = "tenant_"+ID+"_wordpress"
    ctx = dict(TENANT_ID=ID, DOMAIN=t, DB_PASSWORD=DB_PASSWORD, DB_ROOT_PASSWORD=DB_ROOT_PASSWORD, container_name=container_name, TEMPLATE=TEMPLATE, WEBHOOK_SECRET=WEBHOOK_SECRET)

#  This prevents:
#  - External routing
#  - Accidental exposure
#  - Other tenants reaching this DB
#
#  No Exposed Ports
#    No ports: defined
#    MariaDB not exposed
#    WordPress only reachable via Caddy on proxy_net
#
#  Resource Protection
#
#  Each tenant limited to:
#
#    1 CPU
#    512MB RAM
#    200 PIDs
#
#  Prevents:
#
#   One tenant exhausting host
#   Plugin memory leaks killing system
#
# Security:
#   cap_drop: ALL
#   no-new-privileges
#   tmpfs for /tmp
#   No privileged containers
#   No Docker socket
#   Internal DB network
#
# Proper DB Tuning
#
#   MariaDB is tuned for small-instance hosting:
#   Lower max connections
#   Smaller buffer pool
#   Good isolation mode

    tenant_plane = template.render(**ctx)
    tenant_plane = """
# TEMPLATE: {TEMPLATE}
# DOMAIN: {DOMAIN}
# ID: {TENANT_ID}
 
""".format(**ctx) + tenant_plane
    h.update(tenant_plane.encode("utf-8"))
    tenant_plane_hazz = h.hexdigest()
    os.system("mkdir -p tenants")
    tf = open("tenants/tenantstack-"+t+".yml","w")
    tf.write(tenant_plane)
    tsigf = open("tenants/tenantstack-"+t+".yml.sig","w")
    tsigf.write(tenant_plane_hazz)

