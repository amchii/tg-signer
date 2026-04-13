## 先决条件

工作目录下添加`start.sh`:

```sh
pip install -U tg-signer

# 首次配置时使用，后续注释掉
sleep infinity

# 配置完成后取消注释
# tg-signer run mytasks
```

## 使用预构建镜像

发布版本会同步到 GitHub Container Registry：

- `ghcr.io/amchii/tg-signer:<tag>`
- `ghcr.io/amchii/tg-signer:latest`（当推送合法 Docker tag 格式的 Git tag，例如 `v0.0.0`、`0.0.0`、`v0.0.0-beta` 时更新）
- `ghcr.io/amchii/tg-signer:<tag>-webui`
- `ghcr.io/amchii/tg-signer:latest-webui`（当推送合法 Docker tag 格式的 Git tag，例如 `v0.0.0`、`0.0.0`、`v0.0.0-beta` 时更新）

其中基础镜像默认包含 `speedup` 所需的 `tgcrypto`，`-webui` 变体会额外安装 `gui` 额外依赖（当前包含 `nicegui`）并默认监听 `8080` 端口。
如果你需要使用国内镜像源或调整构建参数，仍然可以继续按下文方式在本地构建。

### 手动测试推送

如果你只想测试 Docker 镜像，而不想因为推送 Git tag 触发 PyPI 发布，可以在 GitHub Actions 中手动运行 `Publish Docker Image` workflow：

- `ref`：要构建的分支、提交或 tag
- `image_tag`：本次测试镜像要推送到 GHCR 的 tag，例如 `manual-test`、`pr-123`、`sha-abcdef`

手动触发时只会推送你指定的测试 tag 和对应的 `-webui` tag，不会覆盖 `latest` 与 `latest-webui`。

### 直接运行预构建镜像

CLI 镜像示例：

```sh
docker run -d --name tg-signer \
  --volume $PWD:/opt/tg-signer \
  --env TG_PROXY=socks5://172.17.0.1:7890 \
  ghcr.io/amchii/tg-signer:latest bash start.sh
```

WebUI 镜像示例：

```sh
docker run -d --name tg-signer-webui \
  --volume $PWD:/opt/tg-signer \
  --publish 8080:8080 \
  --env TG_SIGNER_GUI_AUTHCODE=change-me \
  ghcr.io/amchii/tg-signer:latest-webui
```

## 使用Dockerfile

* ### 构建镜像：

    ```sh
    docker build -t tg-signer:latest -f CN.Dockerfile .
    ```

* ### 运行

    ```sh
    docker run -d --name tg-signer --volume $PWD:/opt/tg-signer --env TG_PROXY=socks5://172.17.0.1:7890 tg-signer:latest bash start.sh
    ```

* ### 指定时区

    构建镜像时可以通过 `TZ` 参数指定时区，例如：

    ```sh
    docker build --build-arg TZ=Europe/Paris -t tg-signer:latest -f CN.Dockerfile .
    ```

    运行容器时再次设置环境变量确保 `TZ` 传递进去（默认值 `Asia/Shanghai`）：

    ```sh
    docker run -d --name tg-signer \
      --volume $PWD:/opt/tg-signer \
      --env TG_PROXY=socks5://172.17.0.1:7890 \
      --env TZ=Europe/Paris \
      tg-signer:latest bash start.sh
    ```

## 或使用Docker Compose

```sh
docker-compose up -d
```

### 可选：调整时区

通过 `TZ` 环境变量可以在启动和构建期间一致地设置时区（默认 `Asia/Shanghai`）。示例：

```sh
TZ=Europe/Paris docker compose up -d
```

如果需要重新构建镜像以更新时区（例如从 `docker compose build`），也可以加上同样的 `TZ` 环境变量：

```sh
TZ=Europe/Paris docker compose build
```

## 配置任务

接下来即可执行 `docker exec -it tg-signer bash` 进入容器进行登录和配置任务操作，见 [README.md](/README.md)。
