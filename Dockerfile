FROM php:8.3-apache
RUN docker-php-ext-install mysqli pdo pdo_mysql
RUN echo "DirectoryIndex tienda.html index.php index.html" > /etc/apache2/conf-available/dirindex.conf && a2enconf dirindex
COPY app/ /var/www/html/
