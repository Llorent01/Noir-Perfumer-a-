FROM php:8.3-apache
RUN docker-php-ext-install mysqli pdo pdo_mysql
COPY app/ /var/www/html/
RUN echo '<?php header("Location: /templates/tienda.html"); ?>' > /var/www/html/index.php
