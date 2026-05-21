# Stage 1: Build React PWA
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

ARG VITE_GRAFANA_DASHBOARD_URL
ENV VITE_GRAFANA_DASHBOARD_URL=$VITE_GRAFANA_DASHBOARD_URL

# Copy all files and build the production bundle
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Clean up default Nginx index.html
RUN rm -rf /usr/share/nginx/html/*

# Copy built React files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.d/ /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/*.sh

# Replace default Nginx configuration with our custom config.
# Local builds use HTTP-only nginx.conf; production compose selects nginx.prod.conf.
ARG NGINX_CONF=nginx.conf
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
