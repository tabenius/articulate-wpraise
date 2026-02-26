FROM wordpress:6.7-php8.3-apache

# Install WP-CLI, MySQL client, dropbear SSH server, and sudo
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-mysql-client \
        dropbear-bin \
        openssh-client \
        sudo \
    && rm -rf /var/lib/apt/lists/* \
    && curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x wp-cli.phar \
    && mv wp-cli.phar /usr/local/bin/wp

# Create user with uid 1000 for SSH access
RUN useradd -m -u 1000 -s /bin/bash wpuser \
    && usermod -aG www-data wpuser \
    && printf 'Defaults env_keep += "WORDPRESS_DB_HOST WORDPRESS_DB_NAME WORDPRESS_DB_USER WORDPRESS_DB_PASSWORD"\nwpuser ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/wpuser \
    && chmod 0440 /etc/sudoers.d/wpuser

# Create WP-CLI config so wp commands find WordPress automatically
# Both for the SSH user and for root (when using sudo)
RUN mkdir -p /home/wpuser/.wp-cli /root/.wp-cli \
    && printf "path: /var/www/html\n" > /home/wpuser/.wp-cli/config.yml \
    && printf "path: /var/www/html\n" > /root/.wp-cli/config.yml \
    && chown -R wpuser:wpuser /home/wpuser/.wp-cli

# Create dropbear directory
RUN mkdir -p /etc/dropbear

# Copy PHP upload configuration
COPY uploads.ini /usr/local/etc/php/conf.d/uploads.ini

# Copy setup scripts
COPY setup.sh /usr/local/bin/wp-setup.sh
COPY update-mcp-connection.sh /usr/local/bin/update-mcp-connection.sh
RUN chmod +x /usr/local/bin/wp-setup.sh /usr/local/bin/update-mcp-connection.sh

# Copy migration system
COPY run-migrations.sh /usr/local/bin/run-migrations.sh
RUN chmod +x /usr/local/bin/run-migrations.sh
COPY migrations /usr/local/migrations
RUN chmod +x /usr/local/migrations/*.sh

# Copy custom plugins to a temporary location
# (will be moved during setup since /var/www/html is a volume)
COPY plugins /tmp/articulate-plugins/

# Copy must-use plugins (these enable core functionality)
COPY mu-plugins /tmp/articulate-mu-plugins/

# Copy SSH entrypoint wrapper
COPY docker-entrypoint-ssh.sh /usr/local/bin/docker-entrypoint-ssh.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-ssh.sh

EXPOSE 2222

ENTRYPOINT ["docker-entrypoint-ssh.sh"]
CMD ["apache2-foreground"]
