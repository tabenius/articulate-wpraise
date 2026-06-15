#!/bin/bash
set -e

DOMAIN="${MAIL_DOMAIN:-ragbaz.cc}"
HOSTNAME="${MAIL_HOSTNAME:-mail.ragbaz.cc}"

echo "Configuring Postfix for domain: $DOMAIN (hostname: $HOSTNAME)"

# Set hostname
echo "$HOSTNAME" > /etc/mailname
postconf -e "myhostname = $HOSTNAME"
postconf -e "mydomain = $DOMAIN"
postconf -e "myorigin = $DOMAIN"

# Network settings — accept mail from Docker network and localhost
postconf -e "mynetworks = 127.0.0.0/8 172.16.0.0/12 10.0.0.0/8 [::1]/128"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ipv4"

# Destination — accept mail for our domain
postconf -e "mydestination = $HOSTNAME, $DOMAIN, localhost.localdomain, localhost"

# Relay — no open relay
postconf -e "relayhost ="
postconf -e "smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination"

# TLS for submission (port 587)
postconf -e "smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem"
postconf -e "smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key"
postconf -e "smtpd_tls_security_level = may"
postconf -e "smtp_tls_security_level = may"
postconf -e "smtp_tls_CApath = /etc/ssl/certs"

# Enable submission port (587) in master.cf
if ! grep -q "^submission" /etc/postfix/master.cf; then
    cat >> /etc/postfix/master.cf <<'SUBMISSION'

submission inet n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=encrypt
  -o smtpd_sasl_auth_enable=no
  -o smtpd_relay_restrictions=permit_mynetworks,reject
  -o smtpd_recipient_restrictions=permit_mynetworks,reject
SUBMISSION
fi

# Size limits
postconf -e "message_size_limit = 10240000"
postconf -e "mailbox_size_limit = 51200000"

# Logging to stdout for Docker
postconf -e "maillog_file = /dev/stdout"

# Create mail aliases
newaliases 2>/dev/null || true

echo "Postfix configured. Starting..."
exec "$@"
