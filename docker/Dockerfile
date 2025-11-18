FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y gcc && \
    mkdir -p build && \
    pip wheel -w build tgcrypto

FROM python:3.12-slim

ARG TZ=Asia/Shanghai
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive
COPY --from=builder /build/*.whl /tmp/

RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

RUN pip install /tmp/*.whl && \
    pip install -U "tg-signer[tgcrypto]"

WORKDIR /opt/tg-signer
