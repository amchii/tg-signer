FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p dist && \
    pip wheel --wheel-dir dist tgcrypto

FROM python:3.12-slim-bookworm AS cli

ARG TZ=Asia/Shanghai
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=builder /build/dist/*.whl /tmp/
WORKDIR /tmp/tg-signer-src
COPY pyproject.toml README.md ./
COPY tg_signer ./tg_signer

RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir /tmp/*.whl && \
    pip install --no-cache-dir . && \
    cd / && rm -rf /tmp/*.whl /tmp/tg-signer-src

WORKDIR /opt/tg-signer

FROM cli AS webui

WORKDIR /tmp/tg-signer-src
COPY pyproject.toml README.md ./
COPY tg_signer ./tg_signer

RUN pip install --no-cache-dir ".[gui]" && \
    cd / && rm -rf /tmp/tg-signer-src

EXPOSE 8080

WORKDIR /opt/tg-signer

CMD ["tg-signer", "webgui", "--host", "0.0.0.0", "--port", "8080"]
