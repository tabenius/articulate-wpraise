FROM wordpress:6.7-php8.3-apache

# Install WP-CLI and MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends default-mysql-client \
    && rm -rf /var/lib/apt/lists/* \
    && curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x wp-cli.phar \
    && mv wp-cli.phar /usr/local/bin/wp

# Copy PHP upload configuration
COPY uploads.ini /usr/local/etc/php/conf.d/uploads.ini

# Copy setup script
COPY setup.sh /usr/local/bin/wp-setup.sh
RUN chmod +x /usr/local/bin/wp-setup.sh

# Copy migration system
COPY run-migrations.sh /usr/local/bin/run-migrations.sh
RUN chmod +x /usr/local/bin/run-migrations.sh
COPY migrations /usr/local/migrations
RUN chmod +x /usr/local/migrations/*.sh
