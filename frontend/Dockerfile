# syntax=docker/dockerfile:1
FROM node:22-alpine AS base

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# --- Development Target ---
FROM base AS dev
RUN npm ci
EXPOSE 5173
CMD ["npm", "run", "dev:web", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- Builder Stage ---
FROM base AS builder
RUN npm ci
COPY . .
RUN npm run build

# --- Production Target ---
FROM node:22-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/build ./build

EXPOSE 3000
CMD ["node", "build"]
