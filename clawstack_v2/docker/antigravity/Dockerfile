FROM node:22-bookworm-slim

# ============================================================
# LAYER 1: Network Tuning
# ============================================================
RUN echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::http::Timeout "60";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::https::Timeout "60";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::https::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99net-tuning

# ============================================================
# LAYER 2-4: Base OS Packages (split by theme)
# ============================================================

# Base CLI tools
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    ca-certificates curl tini git unzip wget gnupg \
    && rm -rf /var/lib/apt/lists/*

# Python + pip + venv
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    python3 python3-pip python3-venv software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# R base (separate - large)
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    r-base \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# LAYER 5-9: Graphics & VNC Stack (each app separate)
# ============================================================

# 3D/OpenGL libs + Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    gmsh xvfb libgl1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

# OpenSCAD (separate - can be large)
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    openscad \
    && rm -rf /var/lib/apt/lists/*

# ffmpeg (separate - very large)
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# VNC stack
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    x11vnc fluxbox imagemagick x11-xserver-utils \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# LAYER 10-11: noVNC (each repo separate)
# ============================================================

# noVNC main repo
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/noVNC

# noVNC websockify (separate - if this fails, above is cached)
RUN git clone --depth 1 https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify

# ============================================================
# LAYER 12-14: FreeCAD AppImage
# DOWNLOAD → EXTRACT → INSTALL are 3 separate layers
# If extract fails, download is NOT re-done
# If install/link fails, download+extract are NOT re-done
# ============================================================

# Step 1: DOWNLOAD ONLY (~700MB - cached on success)
RUN wget --progress=dot:giga --tries=5 \
    "https://github.com/FreeCAD/FreeCAD/releases/download/0.21.2/FreeCAD-0.21.2-Linux-x86_64.AppImage" \
    -O /tmp/FreeCAD.AppImage

# Step 2: EXTRACT ONLY (if this fails, re-run only this step)
RUN chmod +x /tmp/FreeCAD.AppImage && \
    cd /tmp && ./FreeCAD.AppImage --appimage-extract

# Step 3: INSTALL + CLEANUP (if links fail, re-run only this step)
RUN mv /tmp/squashfs-root /opt/freecad && \
    ln -s /opt/freecad/AppRun /usr/local/bin/freecad && \
    ln -s /opt/freecad/usr/bin/FreeCADCmd /usr/local/bin/FreeCADCmd && \
    rm -f /tmp/FreeCAD.AppImage

# ============================================================
# LAYER 15-17: FEM Solvers (each separate)
# ============================================================

# CalculiX FEM solver
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    calculix-ccx \
    && rm -rf /var/lib/apt/lists/*

# Netgen mesh generator
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    netgen \
    && rm -rf /var/lib/apt/lists/*

# OpenFOAM (separate - very large ~1GB)
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    openfoam \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# LAYER 18: Blender (separate - very large)
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    blender \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# LAYER 19-21: ElmerFEM
# MPI DEPS → DOWNLOAD → INSTALL are 3 separate layers
# ============================================================

# Step 1: MPI dependencies
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    libopenmpi3 libopenmpi-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 2: DOWNLOAD ElmerFEM .deb ONLY (cached on success)
RUN BASE_URL="http://ppa.launchpad.net/elmer-csc-ubuntu/elmer-csc-ppa/ubuntu/pool/main/e/elmerfem-csc/" && \
    LATEST_DEB=$(curl -s $BASE_URL | grep -o 'href="elmerfem-csc_[^"]*_amd64.deb"' | head -n 1 | cut -d '"' -f 2) && \
    wget -q "${BASE_URL}${LATEST_DEB}" -O /tmp/elmerfem.deb

# Step 3: INSTALL ONLY (if this fails, download above is still cached)
RUN dpkg -i /tmp/elmerfem.deb || apt-get install -f -y && \
    rm -f /tmp/elmerfem.deb && \
    rm -rf /var/lib/apt/lists/*

ENV ELMER_HOME="/usr/share/elmersolver"

# ============================================================
# LAYER 22-23: OpenRadioss
# DOWNLOAD → INSTALL are 2 separate layers
# ============================================================

# Step 1: DOWNLOAD ONLY (cached on success)
RUN wget -q --tries=5 \
    "https://github.com/OpenRadioss/OpenRadioss/releases/download/latest-20260120/OpenRadioss_linux64.zip" \
    -O /tmp/openradioss.zip

# Step 2: EXTRACT + INSTALL + CLEANUP
RUN unzip /tmp/openradioss.zip -d /opt/ && \
    rm /tmp/openradioss.zip && \
    if [ -d "/opt/OpenRadioss" ]; then mv /opt/OpenRadioss /opt/openradioss; fi && \
    if [ -d "/opt/OpenRadioss_linux64" ]; then mv /opt/OpenRadioss_linux64 /opt/openradioss; fi && \
    ln -sf /opt/openradioss/exec/starter_linux64_gf /usr/local/bin/starter && \
    ln -sf /opt/openradioss/exec/engine_linux64_gf /usr/local/bin/engine && \
    ln -sf /usr/local/bin/starter /usr/local/bin/openradioss_starter && \
    ln -sf /usr/local/bin/engine /usr/local/bin/openradioss_engine

# ============================================================
# LAYER 24-25: Godot Engine
# DOWNLOAD → INSTALL are 2 separate layers
# ============================================================

# Step 1: DOWNLOAD ONLY (cached on success)
RUN wget -q --tries=5 \
    https://github.com/godotengine/godot/releases/download/4.2.1-stable/Godot_v4.2.1-stable_linux.x86_64.zip \
    -O /tmp/godot.zip

# Step 2: EXTRACT + INSTALL + CLEANUP
RUN unzip /tmp/godot.zip -d /opt/ && \
    mv /opt/Godot_v4.2.1-stable_linux.x86_64 /opt/godot && \
    ln -s /opt/godot /usr/local/bin/godot && \
    rm /tmp/godot.zip

# ============================================================
# LAYER 26-27: Rhubarb Lip Sync
# DOWNLOAD → INSTALL are 2 separate layers
# ============================================================

# Step 1: DOWNLOAD ONLY (cached on success)
RUN wget -q --tries=5 \
    https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/Rhubarb-Lip-Sync-1.13.0-Linux.zip \
    -O /tmp/rhubarb.zip

# Step 2: EXTRACT + INSTALL + CLEANUP
RUN unzip /tmp/rhubarb.zip -d /opt/rhubarb && \
    ln -s /opt/rhubarb/Rhubarb-Lip-Sync-1.13.0-Linux/rhubarb /usr/local/bin/rhubarb && \
    rm /tmp/rhubarb.zip

# ============================================================
# LAYER 28: Java (for Impact FEM)
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
    default-jre default-jdk \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# LAYER 29-30: Impact FEM
# DOWNLOAD → INSTALL are 2 separate layers
# ============================================================

# Step 1: DOWNLOAD ONLY (cached on success)
RUN mkdir -p /opt/impact && \
    wget -q --tries=5 \
    "https://sourceforge.net/projects/impact/files/latest/download" \
    -O /tmp/impact.zip

# Step 2: EXTRACT + INSTALL + CLEANUP
RUN unzip /tmp/impact.zip -d /opt/impact/ && \
    rm /tmp/impact.zip && \
    printf '#!/bin/bash\njava -jar /opt/impact/Impact.jar "$@"' > /usr/local/bin/impact && \
    chmod +x /usr/local/bin/impact

# ============================================================
# LAYER 31-33: Node.js tools (each package separate)
# ============================================================
RUN npm install -g @remotion/cli
RUN npm install -g bun
RUN mkdir -p /home/node/remotion_projects && chown -R node:node /home/node/remotion_projects

# ============================================================
# LAYER 34-35: rclone
# DOWNLOAD → INSTALL are 2 separate layers
# ============================================================

# Step 1: DOWNLOAD ONLY (cached on success)
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip

# Step 2: INSTALL + CLEANUP
RUN unzip rclone-current-linux-amd64.zip && \
    cp rclone-*-linux-amd64/rclone /usr/bin/ && \
    chmod 755 /usr/bin/rclone && \
    rm -rf rclone-*

# ============================================================
# LAYER 36-44: Python packages (each package/group separate)
# If one package fails, all previous ones are cached
# ============================================================
RUN pip3 install --no-cache-dir --break-system-packages numpy
RUN pip3 install --no-cache-dir --break-system-packages scipy
RUN pip3 install --no-cache-dir --break-system-packages pandas matplotlib
RUN pip3 install --no-cache-dir --break-system-packages pyvista
RUN pip3 install --no-cache-dir --break-system-packages meshio trimesh
RUN pip3 install --no-cache-dir --break-system-packages aider-chat
RUN pip3 install --no-cache-dir --break-system-packages openai-whisper
RUN pip3 install --no-cache-dir --break-system-packages mujoco pybullet
RUN pip3 install --no-cache-dir --break-system-packages pfta

# ============================================================
# LAYER 45-49: R packages (each package separate)
# If one package fails, all previous ones are cached
# ============================================================
RUN R -e "install.packages('SixSigma',  repos='https://cloud.r-project.org')"
RUN R -e "install.packages('qcc',       repos='https://cloud.r-project.org')"
RUN R -e "install.packages('AlgDesign', repos='https://cloud.r-project.org')"
RUN R -e "install.packages('DoE.wrapper', repos='https://cloud.r-project.org')"
RUN R -e "install.packages('skpr',      repos='https://cloud.r-project.org')"

# ============================================================
# LAYER 50-54: 3D Conversion Toolchain
# ============================================================

# Build tools + locales (separate from LaTeX)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential locales libpng-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# LaTeX (separate - very large ~500MB)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    texlive-latex-extra texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

# Locale config
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# IDTFConverter: CLONE SOURCE ONLY (cached if clone succeeds)
RUN git clone https://github.com/ningfei/u3d.git /tmp/u3d

# IDTFConverter: BUILD + INSTALL (separate - if build fails, clone is cached)
RUN cd /tmp/u3d && \
    CXXFLAGS="-std=c++14" ./configure && make && make install && \
    rm -rf /tmp/u3d

# ============================================================
# LAYER 55-57: 3D Python libs (each package separate)
# ============================================================
RUN pip3 install --no-cache-dir --break-system-packages ezdxf
RUN pip3 install --no-cache-dir --break-system-packages pymeshlab
RUN pip3 install --no-cache-dir --break-system-packages pygltflib

# ============================================================
# LAYER 58-62: Harness Engineering Tools
# Wire harness documentation, electrical design, and calculation
# ============================================================

# Graphviz: required by WireViz for PNG/SVG diagram rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# WireViz: wire harness diagram + BOM generator from YAML definition
RUN pip3 install --no-cache-dir --break-system-packages wireviz

# Schemdraw: electrical schematic drawing library (Python-native)
RUN pip3 install --no-cache-dir --break-system-packages schemdraw

# PySpice: SPICE circuit simulation interface
RUN pip3 install --no-cache-dir --break-system-packages PySpice

# networkx: graph-based harness routing analysis
RUN pip3 install --no-cache-dir --break-system-packages networkx

# ============================================================
# LAYER 63: FreeCADCmd wrapper
# ============================================================
RUN printf '#!/usr/bin/env bash\nexec /opt/freecad/AppRun FreeCADCmd "$@"' \
    > /usr/local/bin/freecadcmd-wrapper && \
    chmod +x /usr/local/bin/freecadcmd-wrapper
ENV FREECADCMD=/usr/local/bin/freecadcmd-wrapper

# ============================================================
# LAYER 59-60: Clawdbot CLI (install + patch separate)
# ============================================================

# Install
RUN npm install -g clawdbot

# Patch (separate - if patch logic changes, only this layer rebuilds)
RUN sed -i 's/const requirePairing = async (reason, _paired) => {/const requirePairing = async (reason, _paired) => { return true; }; const _unused_requirePairing = async (reason, _paired) => {/g' \
    /usr/local/lib/node_modules/clawdbot/dist/gateway/server/ws-connection/message-handler.js

USER node
WORKDIR /home/node
EXPOSE 18789 18791
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["clawdbot","gateway","--port","18789","--bind","lan","--verbose"]
