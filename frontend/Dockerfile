# Stage 1: Build React PWA
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

ARG VITE_YANDEX_MAPS_API_TOKEN
ENV VITE_YANDEX_MAPS_API_TOKEN=$VITE_YANDEX_MAPS_API_TOKEN

ARG VITE_GEOAPIFY_API_KEY
ENV VITE_GEOAPIFY_API_KEY=$VITE_GEOAPIFY_API_KEY

ARG VITE_YANDEX_GEOSUGGEST_API_KEY
ENV VITE_YANDEX_GEOSUGGEST_API_KEY=$VITE_YANDEX_GEOSUGGEST_API_KEY

# Copy all files and build the production bundle
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Clean up default Nginx index.html
RUN rm -rf /usr/share/nginx/html/*

# Copy built React files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Replace default Nginx configuration with our custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
