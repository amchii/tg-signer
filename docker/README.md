# tg-signer Docker 使用指南

## 快速开始

```bash
# 1. 创建目录并进入
mkdir -p /opt/tg-signer/data && cd /opt/tg-signer

# 2. 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/htazq/tg-signer/main/docker/docker-compose.yml

# 3. 启动容器
docker compose up -d

# 4. 进入容器
docker exec -it tg-signer bash
```

## 首次配置

在容器内执行：

```bash
# 1. 登录 Telegram
tg-signer login
# 按提示输入手机号和验证码

# 2. 配置签到任务
tg-signer run my_task
# 按提示配置 Chat ID、签到时间、动作等
# 配置完成后 Ctrl+C 退出

# 3. 退出容器
exit
```

## 启动任务

配置完成后，修改 `docker-compose.yml`：

```yaml
    # 注释掉这行
    # command: ["sleep", "infinity"]
    # 取消注释并填入任务名
    command: ["tg-signer", "run", "任务名1", "任务名2"]
```

然后重启：

```bash
docker compose up -d
docker logs -f tg-signer  # 查看日志确认运行正常
```

## 镜像说明

| 镜像 | 内存占用 | 说明 |
|------|----------|------|
| `ghcr.io/htazq/tg-signer:latest` | ~70MB | 推荐，CLI 版 |
| `ghcr.io/htazq/tg-signer:latest-webui` | ~110MB | 包含 Web 管理界面 |

支持平台：`linux/amd64`、`linux/arm64`

## 环境变量

| 变量 | 说明 |
|------|------|
| `TG_PROXY` | 代理地址，如 `socks5://host:port` |
| `TZ` | 时区，默认 `Asia/Shanghai` |

## 常用命令

```bash
# 查看日志
docker logs -f tg-signer

# 列出已配置的任务
docker exec tg-signer tg-signer list

# 手动执行一次签到
docker exec tg-signer tg-signer run-once 任务名

# 更新镜像
docker compose pull && docker compose up -d
```
