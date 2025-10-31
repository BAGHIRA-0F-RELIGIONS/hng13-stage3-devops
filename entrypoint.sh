#!/bin/sh
set -e

echo "Rendering Nginx configuration..."
envsubst '${PORT} ${ACTIVE_POOL} ${RELEASE_ID}' < /etc/nginx/templates/default.conf.template > /etc/nginx/nginx.conf

echo "Starting Nginx..."
exec nginx -g 'daemon off;'
