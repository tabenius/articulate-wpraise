FROM wordpress:6.7-php8.3-apache

# Install WP-CLI and MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/* \
    && curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x wp-cli.phar \
    && mv wp-cli.phar /usr/local/bin/wp

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
COPY plugins /tmp/wp-ai-plugins/

# Copy must-use plugins (these enable core functionality)
COPY mu-plugins /tmp/wp-ai-mu-plugins/
