#!/bin/sh
ln -sfT "/DockerHelpers/nginx-config/nginx_${NGINX_CONFIG}.conf" "/etc/nginx/conf.d/default.conf"
exec "$@"
