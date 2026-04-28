FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV BLENDER_VERSION=4.2.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    wget curl ca-certificates \
    libxi6 libxrender1 libxext6 libgl1 libgles2 \
    libxkbcommon0 libsm6 libice6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q "https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    -O /tmp/blender.tar.xz \
    && tar -xf /tmp/blender.tar.xz -C /opt/ \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender-${BLENDER_VERSION}-linux-x64/blender /usr/local/bin/blender

RUN pip3 install --no-cache-dir \
    fastapi uvicorn[standard] \
    requests psycopg2-binary

WORKDIR /app
COPY backend/ ./

ENV BLENDER_BIN=/usr/local/bin/blender
ENV IATF_VIDEO_ROOT=/data/iatf_videos

EXPOSE 18797
CMD ["python3", "main.py"]
