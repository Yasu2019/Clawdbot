FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip libgfortran5 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openradioss

# GitHubの「最新リリース資産」直リンクは /releases/latest/download/<asset>
ARG ORS_ASSET=OpenRadioss_linux64.zip
RUN curl -fL --retry 10 --retry-all-errors --connect-timeout 20 --max-time 600 \
    -o openradioss.zip \
    "https://github.com/OpenRadioss/OpenRadioss/releases/latest/download/${ORS_ASSET}" \
    && unzip openradioss.zip \
    && rm openradioss.zip \
    && chmod -R +x /opt/openradioss/exec || true

ENV PATH="/opt/openradioss/exec:${PATH}"
WORKDIR /work
CMD ["bash", "-lc", "sleep infinity"]
