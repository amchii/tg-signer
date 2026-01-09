# tg-signer Docker 使用指南

## 快速开始

```bash
# 1. 创建目录
mkdir -p /opt/tg-signer/data && cd /opt/tg-signer

# 2. 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/htazq/tg-signer/main/docker/docker-compose.yml

# 3. (可选) 修改访问密码
vi docker-compose.yml

# 4. 启动
docker compose up -d

# 5. 访问 http://your-ip:8080 进行配置
```

## 使用流程

### 首次配置

1. 访问 `http://your-ip:8080`，输入访问密码
2. 在 WebUI 中完成 **Telegram 登录**
3. **创建签到任务**：配置 Chat ID、签到时间、动作等
4. 点击 **"运行"** 按钮启动任务
5. 任务会在后台按配置的时间自动执行

> 💡 配置完成后不需要保持浏览器打开，任务会在容器内自动运行

### (可选) 切换到 CLI 版本节省资源

配置完任务后，如果想节省内存（~70MB vs ~110MB），可以切换到 CLI 版：

```yaml
# docker-compose.yml
services:
  tg-signer:
    image: ghcr.io/htazq/tg-signer:latest  # 改为 CLI 版
    command: ["tg-signer", "run", "任务名1", "任务名2"]  # 添加此行
    # ... 其他配置保持不变
```

然后重启：`docker compose up -d`

## 镜像说明

| 镜像 | 内存占用 | 说明 |
|------|----------|------|
| `ghcr.io/htazq/tg-signer:latest-webui` | ~110MB | 推荐，包含 Web 管理界面 |
| `ghcr.io/htazq/tg-signer:latest` | ~70MB | 仅 CLI，需配合 command 使用 |

支持平台：`linux/amd64`、`linux/arm64`

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TG_SIGNER_GUI_AUTHCODE` | WebUI 访问密码 | - |
| `TG_PROXY` | 代理地址 | - |
| `TZ` | 时区 | Asia/Shanghai |

## 常用命令

```bash
# 查看日志
docker logs -f tg-signer

# 进入容器 (CLI 操作)
docker exec -it tg-signer bash

# 列出已配置的任务
docker exec tg-signer tg-signer list

# 更新镜像
docker compose pull && docker compose up -d
```

## 本地构建

```bash
# WebUI 版
docker build -t tg-signer:webui -f docker/Dockerfile.webui .

# CLI 版
docker build -t tg-signer -f docker/Dockerfile .

# 中国镜像加速
docker build -t tg-signer -f docker/CN.Dockerfile .
```
