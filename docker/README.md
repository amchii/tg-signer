# tg-signer Docker 使用指南

本目录包含 tg-signer 的 Docker 配置文件，支持多种部署方式。

## 📦 镜像说明

我们提供两种预构建镜像，托管在 GitHub Container Registry:

| 镜像 | 说明 | 拉取命令 |
|------|------|----------|
| `ghcr.io/htazq/tg-signer:latest` | 基础版，仅 CLI | `docker pull ghcr.io/htazq/tg-signer:latest` |
| `ghcr.io/htazq/tg-signer:latest-webui` | WebUI 版 | `docker pull ghcr.io/htazq/tg-signer:latest-webui` |

**支持的平台**: `linux/amd64`, `linux/arm64`

**版本标签**:
- `latest` / `latest-webui` - 最新稳定版
- `v0.8.4` / `v0.8.4-webui` - 指定版本
- `dev` / `dev-webui` - 开发版本

---

## 🚀 快速开始

### 方式一: 使用 Docker Compose (推荐)

1. **创建数据目录并进入 docker 目录**:
   ```bash
   cd docker
   mkdir -p data
   ```

2. **启动 WebUI**:
   ```bash
   # 设置访问密码 (可选但强烈建议)
   export AUTH_CODE="your_secure_password"
   
   # 启动
   docker compose up -d webui
   ```

3. **访问 WebUI**: 打开浏览器访问 `http://localhost:8080`

4. **在 WebUI 中完成**:
   - 登录 Telegram 账号
   - 配置签到任务或监控任务
   - 设置定时运行

### 方式二: 直接使用 Docker

```bash
# 创建数据目录
mkdir -p data

# 启动 WebUI
docker run -d \
  --name tg-signer-webui \
  -p 8080:8080 \
  -v $(pwd)/data:/opt/tg-signer \
  -e TG_SIGNER_GUI_AUTHCODE=your_password \
  -e TZ=Asia/Shanghai \
  ghcr.io/htazq/tg-signer:latest-webui
```

### 方式三: CLI 交互模式

```bash
# 启动容器进入交互模式
docker run -it --rm \
  -v $(pwd)/data:/opt/tg-signer \
  -e TZ=Asia/Shanghai \
  ghcr.io/htazq/tg-signer:latest \
  bash

# 在容器内执行
tg-signer login           # 登录
tg-signer run my_task     # 配置并运行签到
tg-signer monitor run     # 配置并运行监控
```

---

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TZ` | 时区 | `Asia/Shanghai` |
| `TG_PROXY` | 代理地址 | 无 |
| `TG_ACCOUNT` | 账号名称 | `my_account` |
| `TG_SIGNER_GUI_AUTHCODE` | WebUI 访问密码 | 无 (建议设置) |
| `TG_SESSION_STRING` | Session 字符串 | 无 |

### 代理设置

如果需要通过代理访问 Telegram:

```bash
# 使用宿主机代理 (Docker Desktop)
export TG_PROXY=socks5://host.docker.internal:7890

# 使用宿主机代理 (Linux)
export TG_PROXY=socks5://172.17.0.1:7890

# 使用其他代理服务器
export TG_PROXY=socks5://your-proxy:1080
```

---

## 🔧 本地构建

### 构建基础镜像

```bash
# 国际网络
docker build -t tg-signer:latest -f Dockerfile ..

# 中国网络 (使用镜像加速)
docker build -t tg-signer:latest -f CN.Dockerfile ..
```

### 构建 WebUI 镜像

```bash
docker build -t tg-signer:webui -f Dockerfile.webui ..
```

### 指定时区构建

```bash
docker build --build-arg TZ=Europe/Paris -t tg-signer:latest -f Dockerfile ..
```

---

## 📁 目录结构

```
docker/
├── Dockerfile           # 基础镜像
├── Dockerfile.webui     # WebUI 镜像
├── CN.Dockerfile        # 中国镜像加速版
├── docker-compose.yml   # 标准 Compose 配置
├── docker-compose.example.yml  # 完整配置示例
└── README.md            # 本文档
```

挂载的数据目录结构:
```
data/
├── my_account.session   # Telegram session 文件
├── .signer/             # 配置和记录目录
│   ├── signs/           # 签到任务
│   ├── monitors/        # 监控任务
│   └── ...
└── logs/                # 日志目录
```

---

## 📋 Docker Compose 完整示例

参考 `docker-compose.example.yml` 获取包含以下服务的完整配置:

- **webui**: WebUI 管理界面 (端口 8080)
- **signer**: 后台签到服务
- **monitor**: 消息监控服务

使用示例:
```bash
# 复制示例配置
cp docker-compose.example.yml docker-compose.yml

# 编辑配置
vim docker-compose.yml

# 启动 WebUI
docker compose up -d webui

# 查看日志
docker compose logs -f

# 启动监控服务 (需要先取消 profiles)
docker compose --profile monitor up -d
```

---

## 🔄 更新镜像

```bash
# 拉取最新镜像
docker compose pull

# 重新创建容器
docker compose up -d
```

---

## 🐛 常见问题

### 1. 无法连接 Telegram

检查代理配置是否正确:
```bash
docker exec -it tg-signer-webui bash
# 在容器内测试
curl -x $TG_PROXY https://api.telegram.org
```

### 2. Session 失效

删除旧的 session 文件重新登录:
```bash
rm data/*.session
docker compose restart webui
```

### 3. 查看日志

```bash
# 查看容器日志
docker compose logs -f webui

# 查看应用日志
cat data/logs/tg-signer.log
```

### 4. 进入容器调试

```bash
docker exec -it tg-signer-webui bash
```

---

## 🔗 相关链接

- [主项目文档](../README.md)
- [GitHub 仓库](https://github.com/htazq/tg-signer)
- [原作者仓库](https://github.com/amchii/tg-signer)
