示例：

##### 构建镜像：

`docker build -t tg-signer:latest -f CN.Dockerfile .`

##### 运行

工作目录下添加`start.sh`:

```
sleep infinity  # 首次配置时使用，后续注释掉
# tg-signer run mytasks  # 配置完成后取消注释
```

示例命令：

`docker run -d --name tg-signer --volume $PWD:/opt/tg-signer --env TG_PROXY=socks5://172.17.0.1:7890 tg-signer:latest bash start.sh`

接下来即可执行 `docker exec -it tg-signer bash` 进入容器进行登录和配置任务操作，见`README.md`
