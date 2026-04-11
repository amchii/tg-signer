FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY tg_signer ./tg_signer

RUN mkdir -p dist && \
    pip wheel --wheel-dir dist tgcrypto && \
    pip wheel --no-deps --wheel-dir dist .

FROM python:3.12-slim AS cli

ARG TZ=Asia/Shanghai
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=builder /build/dist/*.whl /tmp/

RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

WORKDIR /opt/tg-signer

FROM cli AS webui

RUN pip install --no-cache-dir nicegui

EXPOSE 8080

CMD ["tg-signer", "webgui", "--host", "0.0.0.0", "--port", "8080"]
