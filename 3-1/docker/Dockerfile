# ==============================================================================
# Bonus 2: Docker Container Web Service Deployment
# Base image: Lightweight official Nginx on Alpine Linux
# ==============================================================================
FROM nginx:1.25-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration with /health endpoint
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Copy web application HTML
COPY ./index.html /usr/share/nginx/html/index.html

# Expose HTTP port 80
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
