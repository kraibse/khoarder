# ── Stage 1: Build ────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────
FROM nginx:alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# ── Dev stage (used by docker-compose.dev.yml) ────────────────
FROM node:22-alpine AS dev

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
