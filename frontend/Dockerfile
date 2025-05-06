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