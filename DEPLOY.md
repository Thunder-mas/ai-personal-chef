# 部署指南：把 AI 私人厨师部署到公网（Docker 一键上线）

目标：让任何人在浏览器打开 `http://你的服务器IP` 就能用——拍照识别食材、对话推荐菜谱。简历上放这个链接，比写十行项目描述都管用。

整套架构在一台服务器上跑两个容器：

```
浏览器 ──> [frontend 容器: nginx :80]  ──(同源反代 /api)──>  [backend 容器: FastAPI :8000]
                 静态前端(React 构建产物)                      LangGraph Agent + RAG + 多模态
```
前端 nginx 把 `/api` 反代到后端，两者同源，**不存在跨域问题**。后端不直接对公网开放，只有 nginx 能访问它。

---

## 一、准备一台服务器（约 5 分钟）

- 国内可买**轻量应用服务器**（阿里云/腾讯云），**2 核 2G 起步**，系统选 **Ubuntu 22.04**。
- 在控制台的**防火墙/安全组**放行 **80 端口**（HTTP）。
- 拿到服务器公网 IP，用 SSH 登录（Windows 可用自带的 `ssh root@你的IP`）。

> 想绑域名：国内服务器需先给域名做 **ICP 备案**（约 1-2 周）。赶时间先用 **IP 直接访问**，或用**海外服务器**免备案。

## 二、装 Docker（约 3 分钟）

```bash
curl -fsSL https://get.docker.com | sh        # 一键装 Docker（含 compose 插件）
systemctl enable --now docker
docker compose version                         # 验证：能打印版本就 OK
```

## 三、拉代码 + 填密钥（约 3 分钟）

```bash
git clone https://gitee.com/yhuicheng/ai-personal-chef.git
cd ai-personal-chef

cp .env.example .env
vi .env        # 填入 MIMO_API_KEY / MIMO_BASE_URL / TAVILY_API_KEY（从你本地 .env 拷）
```

> `.env` 含密钥，**只在服务器上存在、绝不提交仓库**（仓库已 `.gitignore` 它）。

## 四、一键启动（约 3-8 分钟，含构建）

```bash
docker compose up -d --build
```

- 第一次会构建镜像、装依赖，稍慢；之后 `docker compose up -d` 秒起。
- 打开浏览器访问 `http://你的服务器IP` 即可。
- **首次发消息**时后端会联网下载约 90MB 的中文 embedding 模型（只下一次，存进挂载卷），稍等十几秒属正常。

## 五、常用运维

```bash
docker compose logs -f backend     # 看后端日志（排查报错）
docker compose logs -f frontend    # 看 nginx 日志
docker compose restart backend     # 重启后端
docker compose down                # 停掉整套
git pull && docker compose up -d --build   # 更新代码后重新部署
```

数据都在服务器的 `resources/` 目录（挂载卷）：对话记忆、用户偏好/健身档案、运营埋点库、向量与模型缓存——容器重建也不丢。

## 六、（可选）绑域名 + HTTPS

最省事的方案是在前面再加一个 **Caddy**（自动签发并续期 Let's Encrypt 证书）：

```
# Caddyfile
你的域名.com {
    reverse_proxy localhost:80
}
```
`caddy run` 即可获得 `https://你的域名.com`。或用 `nginx + certbot` 手动签证书。

---

## 排错速查

| 现象 | 原因 / 解决 |
|---|---|
| 打不开网页 | 安全组没放行 80；或 `docker compose ps` 看容器是否在跑 |
| 网页能开、发消息报错 | `.env` 没填对；`docker compose logs backend` 看具体报错 |
| 回复不是逐字出现、卡很久才整段出 | nginx 没关缓冲——本仓库 `nginx.conf` 已设 `proxy_buffering off`，确认用的是它 |
| 第一条消息特别慢 | 在下载 embedding 模型，正常，只首次 |
| 前端构建失败 | 本地先 `cd frontend && npm run build` 看 TS 报错并修掉 |

> 把后端单独部署（不走 nginx 同源）才需要改 CORS：在 `api/server.py` 的 `allow_origins` 里加上你的前端域名。本方案同源代理，无需改动。
