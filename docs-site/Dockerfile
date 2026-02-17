# Dockerfile for WP-AI Documentation Site
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy documentation
COPY . .

# Build static site
RUN npm run docs:build

# Production stage
FROM nginx:alpine

# Copy built docs to nginx
COPY --from=builder /app/.vitepress/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
