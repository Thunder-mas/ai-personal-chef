# 前端镜像：第一阶段用 Node 构建 React，第二阶段用 nginx 托管静态文件并反代 /api。
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
# 构建产物 → nginx 站点根目录
COPY --from=build /app/dist /usr/share/nginx/html
# 自定义配置：SPA 路由回退 + /api 反代到后端容器（同源，免跨域）
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
