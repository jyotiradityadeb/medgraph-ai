FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci --silent
COPY . .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s CMD curl -sf http://localhost/ > /dev/null || exit 1
CMD ["nginx", "-g", "daemon off;"]

