#!/bin/bash
set -e

# =============================================================================
# Dropbear SSH Server + WordPress Entrypoint Wrapper
# =============================================================================

SSH_USER="wpuser"
SSH_HOME="/home/$SSH_USER"
SSH_DIR="$SSH_HOME/.ssh"
DROPBEAR_DIR="/etc/dropbear"

mkdir -p "$DROPBEAR_DIR" "$SSH_DIR"

# Generate dropbear host keys if they don't exist
for keytype in rsa ecdsa ed25519; do
    keyfile="$DROPBEAR_DIR/dropbear_${keytype}_host_key"
    if [ ! -f "$keyfile" ]; then
        echo "[SSH] Generating $keytype host key..."
        dropbearkey -t "$keytype" -f "$keyfile" > /dev/null 2>&1 || true
    fi
done

# Generate user SSH key pair if it doesn't exist
if [ ! -f "$SSH_DIR/id_ed25519" ]; then
    echo "[SSH] Generating user key pair..."
    ssh-keygen -t ed25519 -f "$SSH_DIR/id_ed25519" -N "" -C "${SSH_USER}@wp-ai-wordpress" -q
    cp "$SSH_DIR/id_ed25519.pub" "$SSH_DIR/authorized_keys"
fi

# Ensure authorized_keys is current
if [ ! -f "$SSH_DIR/authorized_keys" ]; then
    cp "$SSH_DIR/id_ed25519.pub" "$SSH_DIR/authorized_keys"
fi

# Fix permissions
chown -R "$SSH_USER:$SSH_USER" "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "$SSH_DIR/id_ed25519" "$SSH_DIR/authorized_keys" 2>/dev/null || true
chmod 644 "$SSH_DIR/id_ed25519.pub" 2>/dev/null || true

# Export Docker environment variables so SSH sessions can access them
# (SSH sessions don't inherit Docker env vars, causing WP-CLI db commands to fail)
# Only export simple single-line vars to avoid shell parse errors
: > /etc/profile.d/wp-env.sh
for var in WORDPRESS_DB_HOST WORDPRESS_DB_NAME WORDPRESS_DB_USER WORDPRESS_DB_PASSWORD WORDPRESS_DB_CHARSET WORDPRESS_DB_COLLATE; do
    val="$(printenv "$var" 2>/dev/null || true)"
    if [ -n "$val" ]; then
        printf 'export %s="%s"\n' "$var" "$val" >> /etc/profile.d/wp-env.sh
    fi
done
printf 'export PATH="%s"\n' "$PATH" >> /etc/profile.d/wp-env.sh
chmod 644 /etc/profile.d/wp-env.sh

# Echo public key
echo ""
echo "========================================="
echo "  SSH Public Key (dropbear @ port 2222)"
echo "========================================="
cat "$SSH_DIR/id_ed25519.pub"
echo "========================================="
echo ""
echo "  To connect, extract the private key:"
echo "    docker cp wp-ai-wordpress:${SSH_DIR}/id_ed25519 /tmp/wp-ai-key"
echo "    chmod 600 /tmp/wp-ai-key"
echo "    ssh -i /tmp/wp-ai-key -p 2222 ${SSH_USER}@localhost"
echo ""
echo "  WP-CLI is available inside the container:"
echo "    wp --allow-root <command>"
echo "    sudo -u www-data wp <command>"
echo "========================================="
echo ""

# Start dropbear SSH daemon in background
echo "[SSH] Starting dropbear SSH server on port 2222..."
dropbear -E -p 2222 2>&1 &

# Execute original WordPress entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"
