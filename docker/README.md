# tg-signer Docker 使用指南

## 快速开始

```bash
# 1. 创建目录
mkdir -p /opt/tg-signer/data && cd /opt/tg-signer

# 2. 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/htazq/tg-signer/main/docker/docker-compose.yml

# 3. 启动容器
docker compose up -d

# 4. 进入容器完成登录和配置
docker exec -it tg-signer bash
```

## 使用流程

### 1. 登录 Telegram（必须在命令行完成）

```bash
docker exec -it tg-signer bash
tg-signer login
# 按提示输入手机号和验证码
```

### 2. 配置签到任务

```bash
tg-signer run my_task
# 按提示配置 Chat ID、签到时间、动作等
```

### 3. 运行任务

配置完成后，修改 `docker-compose.yml` 添加启动命令：

```yaml
services:
  tg-signer:
    image: ghcr.io/htazq/tg-signer:latest
    command: ["tg-signer", "run", "任务名1", "任务名2"]
    # ... 其他配置
```

然后重启：`docker compose up -d`

任务会在后台按配置的时间自动执行。

## 镜像说明

| 镜像 | 内存占用 | 说明 |
|------|----------|------|
| `ghcr.io/htazq/tg-signer:latest` | ~70MB | 推荐，CLI 版 |
| `ghcr.io/htazq/tg-signer:latest-webui` | ~110MB | 包含 Web 配置界面 |

支持平台：`linux/amd64`、`linux/arm64`

## 环境变量

| 变量 | 说明 |
|------|------|
| `TG_PROXY` | 代理地址，如 `socks5://host:port` |
| `TZ` | 时区，默认 `Asia/Shanghai` |
| `TG_SIGNER_GUI_AUTHCODE` | WebUI 访问密码（仅 webui 版） |

## 常用命令

```bash
# 查看日志
docker logs -f tg-signer

# 列出已配置的任务
docker exec tg-signer tg-signer list

# 更新镜像
docker compose pull && docker compose up -d
```
