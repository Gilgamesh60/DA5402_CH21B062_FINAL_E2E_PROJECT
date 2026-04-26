# Phase 1 stub: static nginx page. Phase 7 replaces with a React build.
FROM nginx:1.25-alpine

COPY docker/frontend/index.html /usr/share/nginx/html/index.html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
