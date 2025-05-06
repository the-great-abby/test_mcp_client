# --- Production build (static site, served by nginx) ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm install || pnpm install || yarn install
COPY . .
RUN npm run build || pnpm build || yarn build

FROM nginx:alpine AS prod
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# --- Development build (hot reload) ---
FROM node:20-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm install || pnpm install || yarn install
COPY . .
EXPOSE 5173
CMD ["yarn", "dev", "--host"] 