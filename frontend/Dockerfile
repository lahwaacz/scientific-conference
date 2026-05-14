# =========================================
# Stage 1: Build the React (Vite) Application
# =========================================

ARG NODE_VERSION=24.14.0-alpine
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

# FIXME: this should not be hardcoded
ARG REACT_APP_BACKEND_API_BASE_URL=https://mmg-webapps.fjfi.cvut.cz/conference-demo

# Build the React.js application (outputs to /app/build)
RUN npm run build


## =========================================
## Stage 2: Serve static files + proxy API requests with nginx
## =========================================
FROM quay.io/nginx/nginx-unprivileged:1-alpine-slim AS runner

# Switch to root for the following RUN and COPY
USER root

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx config
#COPY nginx.conf /etc/nginx/nginx.conf

# Switch back to the unprivileged nginx user
USER 101

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
