# tg-signer Docker 使用指南

## 快速开始

```bash
# 1. 创建目录
mkdir -p /opt/tg-signer/data && cd /opt/tg-signer

# 2. 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/htazq/tg-signer/main/docker/docker-compose.yml

# 3. 启动
docker compose up -d

# 4. 访问 http://your-ip:8080
```

## 镜像

| 镜像 | 说明 |
|------|------|
| `ghcr.io/htazq/tg-signer:latest-webui` | WebUI 版 (推荐) |
| `ghcr.io/htazq/tg-signer:latest` | 仅 CLI |

支持 `linux/amd64` 和 `linux/arm64`

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TG_SIGNER_GUI_AUTHCODE` | WebUI 访问密码 | - |
| `TG_PROXY` | 代理地址 | - |
| `TZ` | 时区 | Asia/Shanghai |

## 代理配置

```yaml
environment:
  # Docker Desktop (Mac/Windows)
  - TG_PROXY=socks5://host.docker.internal:7890
  # Linux
  - TG_PROXY=socks5://172.17.0.1:7890
```

## 常用命令

```bash
# 查看日志
docker logs -f tg-signer

# 进入容器
docker exec -it tg-signer bash

# 更新镜像
docker compose pull && docker compose up -d
```

## 本地构建

```bash
# 基础版
docker build -t tg-signer -f docker/Dockerfile .

# WebUI 版
docker build -t tg-signer:webui -f docker/Dockerfile.webui .

# 中国镜像加速
docker build -t tg-signer -f docker/CN.Dockerfile .
```
