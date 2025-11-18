## 先决条件

工作目录下添加`start.sh`:

```sh
pip install -U tg-signer

# 首次配置时使用，后续注释掉
sleep infinity

# 配置完成后取消注释
# tg-signer run mytasks
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
