## 先决条件

工作目录下添加`start.sh`:

```sh
pip install -U tg-signer

# 首次配置时使用，后续注释掉
sleep infinity

# 配置完成后取消注释
# tg-signer run mytasks

# 如需同时运行多个任务
# tg-signer run mytask1 &
# tg-signer run mytask2 &
# tg-signer run mytask3

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

## 或使用Docker Compose

```sh
docker-compose up -d
```

## 配置任务

接下来即可执行 `docker exec -it tg-signer bash` 进入容器进行登录和配置任务操作，见 [README.md](/README.md)。
