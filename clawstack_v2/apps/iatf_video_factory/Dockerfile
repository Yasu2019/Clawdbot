FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV BLENDER_VERSION=4.2.0

# ── 基本ツール + Python ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev \
    wget curl ca-certificates \
    libxi6 libxrender1 libxext6 libgl1 libgles2 \
    libxkbcommon0 libsm6 libice6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ── Blender headless ────────────────────────────────────────────
RUN wget -q "https://download.blender.org/release/Blender4.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    -O /tmp/blender.tar.xz \
    && tar -xf /tmp/blender.tar.xz -C /opt/ \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender-${BLENDER_VERSION}-linux-x64/blender /usr/local/bin/blender

# ── Rhubarb Lip Sync ────────────────────────────────────────────
RUN wget -q "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/rhubarb-lip-sync-1.13.0-linux.zip" \
    -O /tmp/rhubarb.zip \
    && apt-get update && apt-get install -y --no-install-recommends unzip \
    && unzip /tmp/rhubarb.zip -d /opt/rhubarb \
    && ln -s /opt/rhubarb/rhubarb /usr/local/bin/rhubarb \
    && rm /tmp/rhubarb.zip \
    && rm -rf /var/lib/apt/lists/*

# ── Python依存 ────────────────────────────────────────────────
RUN pip3 install --no-cache-dir \
    requests \
    pdfplumber \
    psycopg2-binary \
    wave

# ── アプリコード ──────────────────────────────────────────────
WORKDIR /app
COPY pipeline/ ./pipeline/

ENV BLENDER_BIN=/usr/local/bin/blender
ENV RHUBARB_BIN=/usr/local/bin/rhubarb
ENV IATF_VIDEO_OUTPUT=/data/iatf_videos
ENV IATF_AUDIO_CACHE=/tmp/iatf_audio

CMD ["python3", "pipeline/orchestrator.py", "--limit", "1"]
