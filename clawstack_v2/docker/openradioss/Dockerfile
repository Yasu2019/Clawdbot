FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip libgfortran5 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openradioss

ARG ORS_ASSET=OpenRadioss_linux64.zip
RUN curl -fL --retry 10 --retry-all-errors --connect-timeout 20 --max-time 600 \
    -o openradioss.zip \
    "https://github.com/OpenRadioss/OpenRadioss/releases/latest/download/${ORS_ASSET}" \
    && unzip openradioss.zip \
    && rm openradioss.zip \
    && chmod -R +x /opt/openradioss/OpenRadioss/exec || true

ENV ORS_ROOT=/opt/openradioss/OpenRadioss
ENV PATH="${ORS_ROOT}/exec:${PATH}"
ENV LD_LIBRARY_PATH="${ORS_ROOT}/exec:${ORS_ROOT}/extlib/hm_reader/linux64"
ENV RAD_CFG_PATH="${ORS_ROOT}/hm_cfg_files"
WORKDIR /work
CMD ["bash", "-lc", "sleep infinity"]
