FROM debian:12-slim

ARG GODOT_VERSION=4.6.1
ARG GODOT_RELEASE=stable
ARG ANDROID_CMDLINE_TOOLS_ZIP_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends     ca-certificates curl unzip wget     python3 python3-pip     openjdk-17-jre-headless     git   && rm -rf /var/lib/apt/lists/*

# Android SDK
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools
RUN wget -O /tmp/cmdline-tools.zip ${ANDROID_CMDLINE_TOOLS_ZIP_URL}   && unzip /tmp/cmdline-tools.zip -d ${ANDROID_HOME}/cmdline-tools   && mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest   && rm /tmp/cmdline-tools.zip

ENV PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${PATH}"

RUN yes | sdkmanager --licenses >/dev/null 2>&1 || true &&     sdkmanager --install       "platform-tools"       "platforms;android-34"       "build-tools;34.0.0"

# Godot binary + export templates
RUN mkdir -p /opt/godot /root/.local/share/godot/export_templates

ARG GODOT_HEADLESS_URL="https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-${GODOT_RELEASE}/Godot_v${GODOT_VERSION}-${GODOT_RELEASE}_linux.x86_64.zip"
ARG GODOT_TEMPLATES_URL="https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-${GODOT_RELEASE}/Godot_v${GODOT_VERSION}-${GODOT_RELEASE}_export_templates.tpz"

RUN wget -O /tmp/godot.zip ${GODOT_HEADLESS_URL}   && unzip /tmp/godot.zip -d /opt/godot   && rm /tmp/godot.zip   && ln -s /opt/godot/Godot_v${GODOT_VERSION}-${GODOT_RELEASE}_linux.x86_64 /usr/local/bin/godot

RUN wget -O /tmp/templates.tpz ${GODOT_TEMPLATES_URL}   && mkdir -p /tmp/tpl   && unzip /tmp/templates.tpz -d /tmp/tpl   && rm /tmp/templates.tpz   && mkdir -p /root/.local/share/godot/export_templates/${GODOT_VERSION}.${GODOT_RELEASE}   && cp -r /tmp/tpl/templates/* /root/.local/share/godot/export_templates/${GODOT_VERSION}.${GODOT_RELEASE}/   && rm -rf /tmp/tpl

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY app /app/app

EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
