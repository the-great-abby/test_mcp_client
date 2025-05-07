# Use Node.js LTS as base image
FROM node:20-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm install

COPY . .
# COPY .env.example .env

ENV NODE_ENV=development
ENV VITE_HOST=0.0.0.0
ENV VITE_PORT=3000

EXPOSE 3000

CMD ["./node_modules/.bin/vite", "--host", "0.0.0.0", "--port", "3000"]

# --- Build stage ---
FROM node:20-slim as build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install && npm install -g serve
COPY . .
RUN npm run build

# --- Production stage ---
FROM node:20-slim as production
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./
EXPOSE 4173 80
CMD ["npx", "serve", "-s", "dist", "-l", "4173"] 