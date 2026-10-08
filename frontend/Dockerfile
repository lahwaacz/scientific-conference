# =========================================
# Stage 1: Build the React (Vite) Application
# =========================================

ARG NODE_VERSION=24.14.0-alpine@sha256:7fddd9ddeae8196abf4a3ef2de34e11f7b1a722119f91f28ddf1e99dcafdf114
# Use a lightweight Node.js image for building (customizable via ARG)
FROM node:${NODE_VERSION} AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy package-related files first to leverage Docker's caching mechanism
COPY package.json package-lock.json ./

# Install project dependencies using npm ci (ensures a clean, reproducible install)
RUN --mount=type=cache,target=/root/.npm npm ci

# Copy the rest of the application source code into the container
COPY . .

# Runtime values default to empty: the image is universal and works under
# any base path. Set BASE_PATH (and optionally API_BASE) on the container
# to configure it at startup; see docker-entrypoint.d/20-app-config.sh.
# In dev, .env.development provides VITE_BACKEND_API_BASE_URL.
ARG VITE_BACKEND_API_BASE_URL=
# Relative Vite base: asset URLs resolve against the served page, and the
# nginx config serves them at any path depth (see nginx.conf).
ARG VITE_BASE_PATH=./
# ARG does not reach RUN commands' environment; export it so Vite can inline it into the bundle
ENV VITE_BACKEND_API_BASE_URL=${VITE_BACKEND_API_BASE_URL}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

# Build the React.js application (outputs to /app/build)
RUN npm run build


## =========================================
## Stage 2: Serve static files + proxy API requests with nginx
## =========================================
FROM quay.io/nginx/nginx-unprivileged:1-alpine-slim@sha256:1517d8c358e2e093957ebee087afa9eb19a32f5d7ecb711b7429e369cb998224 AS runner

# Switch to root for the following RUN and COPY
USER root

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Universal server config (no deployment values) and the runtime-config
# entrypoint script. Only app-config.js is writable by the unprivileged
# user (the entrypoint overwrites it in place); the rest of the tree
# stays root-owned read-only.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/20-app-config.sh /docker-entrypoint.d/20-app-config.sh
RUN chmod +x /docker-entrypoint.d/20-app-config.sh \
    && chown 101:0 /usr/share/nginx/html/app-config.js

# Switch back to the unprivileged nginx user
USER 101

EXPOSE 8000
CMD ["nginx", "-g", "daemon off;"]
