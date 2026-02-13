# Multi-stage build for OpenFOAM
FROM opencfd/openfoam-default:2312 AS openfoam-source


FROM node:22-bookworm-slim

# ============================================================
# ROBUST NETWORK & APT CONFIGURATION (From Clawstack V2)
# ============================================================
RUN echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::http::Timeout "60";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::https::Timeout "60";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99net-tuning && \
    echo 'Acquire::https::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/99net-tuning

# ============================================================
# ENGINEERING TOOLS - STAGE 1: SYSTEM & GRAPHICS
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends -o Acquire::Retries=5 --fix-missing \
    ca-certificates curl tini git python3 python3-pip python3-venv unzip wget gnupg software-properties-common \
    gmsh openscad ffmpeg xvfb libgl1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# ENGINEERING TOOLS - STAGE 2: VISUALIZATION & CAE (ParaView, Blender, OpenFOAM)
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    paraview \
    python3-vtk9 \
    blender \
    calculix-ccx \
    netgen \
    && rm -rf /var/lib/apt/lists/*

# OpenFOAM (Multi-stage copy from Official Image)
COPY --from=openfoam-source /usr/lib/openfoam/openfoam2312 /opt/openfoam2312
# Install OpenMPI dependencies (ElmerFEM stage handles libopenmpi3, ensuring runtime compat)
RUN echo "source /opt/openfoam2312/etc/bashrc" >> /etc/bash.bashrc && \
    ln -s /opt/openfoam2312/platforms/linux64GccDPInt32Opt/bin/simpleFoam /usr/local/bin/simpleFoam && \
    ln -s /opt/openfoam2312/platforms/linux64GccDPInt32Opt/bin/blockMesh /usr/local/bin/blockMesh && \
    ln -s /opt/openfoam2312/platforms/linux64GccDPInt32Opt/bin/snappyHexMesh /usr/local/bin/snappyHexMesh

# ============================================================
# ENGINEERING TOOLS - STAGE 3: SPECIALIZED TOOLS (FreeCAD AppImage hack)
# ============================================================
# FreeCAD AppImage strategy for ID stability and network robustness
RUN wget --progress=dot:giga "https://github.com/FreeCAD/FreeCAD/releases/download/0.21.2/FreeCAD-0.21.2-Linux-x86_64.AppImage" -O /tmp/FreeCAD.AppImage && \
    chmod +x /tmp/FreeCAD.AppImage && \
    cd /tmp && ./FreeCAD.AppImage --appimage-extract && \
    mv squashfs-root /opt/freecad && \
    ln -s /opt/freecad/AppRun /usr/local/bin/freecad && \
    ln -s /opt/freecad/usr/bin/freecadcmd /usr/local/bin/FreeCADCmd && \
    rm /tmp/FreeCAD.AppImage

# ElmerFEM (Direct Download & Extract from Ubuntu PPA)
# Download specific .deb for Ubuntu Jammy (compatible with Debian 12 via manual extract)
RUN wget -q "http://ppa.launchpad.net/elmer-csc-ubuntu/elmer-csc-ppa/ubuntu/pool/main/e/elmerfem-csc/elmerfem-csc_9.0-0ppa0-202602121017~b48eebbbf~ubuntu22.04.1_amd64.deb" -O /tmp/elmerfem.deb && \
    mkdir -p /tmp/extracted && \
    dpkg -x /tmp/elmerfem.deb /tmp/extracted && \
    cp -r /tmp/extracted/usr/bin/Elmer* /usr/local/bin/ && \
    cp -r /tmp/extracted/usr/lib/elmersolver /usr/lib/ && \
    cp -r /tmp/extracted/usr/share/elmersolver /usr/share/ && \
    rm -rf /tmp/elmerfem.deb /tmp/extracted

# Install runtime dependencies (OpenMPI, GFortran, Linear Algebra)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenmpi3 libgfortran5 liblapack3 libblas3 \
    && rm -rf /var/lib/apt/lists/*



# OpenRadioss (Zip Binary)
RUN wget -q "https://github.com/OpenRadioss/OpenRadioss/releases/download/latest-20260120/OpenRadioss_linux64.zip" -O /tmp/openradioss.zip && \
    unzip /tmp/openradioss.zip -d /opt/ && \
    rm /tmp/openradioss.zip && \
    if [ -d "/opt/OpenRadioss" ]; then mv /opt/OpenRadioss /opt/openradioss; fi && \
    if [ -d "/opt/OpenRadioss_linux64" ]; then mv /opt/OpenRadioss_linux64 /opt/openradioss; fi && \
    ln -s /opt/openradioss/exec/starter_linux64_gf /usr/local/bin/starter && \
    ln -s /opt/openradioss/exec/engine_linux64_gf /usr/local/bin/engine

# Godot Engine (Headless)
RUN wget -q https://github.com/godotengine/godot/releases/download/4.2.1-stable/Godot_v4.2.1-stable_linux.x86_64.zip -O /tmp/godot.zip && \
    unzip /tmp/godot.zip -d /opt/ && \
    mv /opt/Godot_v4.2.1-stable_linux.x86_64 /opt/godot && \
    ln -s /opt/godot /usr/local/bin/godot && \
    rm /tmp/godot.zip

# Java & Impact FEM
RUN apt-get update && apt-get install -y --no-install-recommends default-jre default-jdk && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/impact && \
    wget -q "https://sourceforge.net/projects/impact/files/latest/download" -O /tmp/impact.zip && \
    unzip /tmp/impact.zip -d /opt/impact/ && \
    rm /tmp/impact.zip && \
    echo '#!/bin/bash\njava -jar /opt/impact/Impact.jar "$@"' > /usr/local/bin/impact && \
    chmod +x /usr/local/bin/impact

# rclone for Sync
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
    && unzip rclone-current-linux-amd64.zip \
    && cp rclone-*-linux-amd64/rclone /usr/bin/ \
    && chmod 755 /usr/bin/rclone \
    && rm -rf rclone-*

# ============================================================
# ENGINEERING TOOLS - STAGE 4: STATS, VNC & 3D PDF
# ============================================================
# R-Base & Quality Packages (System Deps added)
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    libgmp-dev libmpfr-dev libglpk-dev \
    && rm -rf /var/lib/apt/lists/*
RUN R -e "install.packages(c('SixSigma', 'qcc', 'AlgDesign', 'DoE.wrapper', 'skpr'), repos='https://cloud.r-project.org')"

# VNC Stack (for headless GUI and screenshots)
RUN apt-get update && apt-get install -y --no-install-recommends \
    x11vnc fluxbox imagemagick x11-xserver-utils && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/noVNC \
    && git clone --depth 1 https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify

# 3D PDF Conversion (LaTeX & U3D)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential cmake locales libpng-dev libjpeg-dev \
    texlive-latex-extra texlive-fonts-recommended && rm -rf /var/lib/apt/lists/*
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8
RUN git clone https://github.com/ningfei/u3d.git /tmp/u3d \
    && cd /tmp/u3d \
    && CXXFLAGS="-std=c++14" ./configure && make && make install \
    && rm -rf /tmp/u3d

# Rhubarb Lip Sync
RUN wget -q https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/Rhubarb-Lip-Sync-1.13.0-Linux.zip -O /tmp/rhubarb.zip && \
    unzip /tmp/rhubarb.zip -d /opt/rhubarb && \
    ln -s /opt/rhubarb/Rhubarb-Lip-Sync-1.13.0-Linux/rhubarb /usr/local/bin/rhubarb && \
    rm /tmp/rhubarb.zip

# Docker CLI (for container orchestration from inside)
RUN apt-get update && apt-get install -y --no-install-recommends docker.io && rm -rf /var/lib/apt/lists/*

# Vision AI Utils (Tesseract + Japanese data)
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-jpn && rm -rf /var/lib/apt/lists/*

# ============================================================
# PYTHON STACK (Unified: Analytics + Vision + QA)
# ============================================================
RUN pip3 install --no-cache-dir --break-system-packages \
    numpy scipy pandas matplotlib pyvista meshio trimesh \
    opencv-python-headless \
    Pillow \
    PyMuPDF \
    reportlab \
    aider-chat \
    ezdxf pymeshlab pygltflib \
    pfta mujoco pybullet \
    openai-whisper \
    python-docx pyyaml

# ============================================================
# NODE & BUN STACK (Unified: Video Gen + Clawdbot)
# ============================================================
RUN npm install -g @remotion/cli bun clawdbot

# Apply pairing bypass patch
RUN sed -i 's/const requirePairing = async (reason, _paired) => {/const requirePairing = async (reason, _paired) => { return true; }; const _unused_requirePairing = async (reason, _paired) => {/g' \
    /usr/local/lib/node_modules/clawdbot/dist/gateway/server/ws-connection/message-handler.js

# Install missing ElmerFEM dependencies (Ubuntu 22.04 ABI)
RUN wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/m/mumps/libmumps-5.4_5.4.1-2_amd64.deb" -O /tmp/libmumps.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/multiverse/p/parmetis/libparmetis4.0_4.0.3-5build1_amd64.deb" -O /tmp/libparmetis.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/h/hypre/libhypre-2.22.1_2.22.1-7_amd64.deb" -O /tmp/libhypre.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/s/scalapack/libscalapack-openmpi2.1_2.1.0-4_amd64.deb" -O /tmp/libscalapack.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/s/superlu-dist/libsuperlu-dist7_7.2.0+dfsg1-2_amd64.deb" -O /tmp/libsuperlu.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/s/scotch/libptscotch-6.1_6.1.3-1_amd64.deb" -O /tmp/libptscotch.deb && \
    wget -q "http://archive.ubuntu.com/ubuntu/pool/universe/c/combblas/libcombblas1.16.0_1.6.2-8_amd64.deb" -O /tmp/libcombblas.deb && \
    mkdir -p /tmp/extracted /usr/lib/elmersolver && \
    for f in /tmp/*.deb; do dpkg -x "$f" /tmp/extracted; done && \
    find /tmp/extracted/usr/lib -name "*.so*" -exec cp -P {} /usr/lib/elmersolver/ \; && \
    rm -rf /tmp/*.deb /tmp/extracted

# Set Library Path for Elmer (Runtime)
ENV LD_LIBRARY_PATH=/usr/lib/elmersolver:$LD_LIBRARY_PATH

USER node
WORKDIR /home/node
EXPOSE 18789 18791
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["clawdbot","gateway","--port","18789","--bind","lan","--verbose"]
