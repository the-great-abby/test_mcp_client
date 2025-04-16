# Use Node.js LTS as base image
FROM node:20-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Copy only the package files needed for the frontend
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the frontend application files
# Exclude task-master directory and its contents
COPY . .
COPY .env.example .env
RUN rm -rf task-master/

# Set environment variables
ENV NODE_ENV=development
ENV VITE_HOST=0.0.0.0
ENV VITE_PORT=3000

# Expose the development server port
EXPOSE 3000

# Command to run the development server using local vite installation
CMD ["./node_modules/.bin/vite", "--host", "0.0.0.0", "--port", "3000"] 