# Stage 1: Python builder - install python3 on normal Alpine
FROM alpine:3.20 AS python-builder
RUN apk add --no-cache python3 py3-pip postgresql-client && \
    pip3 install --no-cache-dir --break-system-packages beautifulsoup4 python-dateutil requests psycopg2-binary

# Stage 2: n8n with docker-cli + python
FROM n8nio/n8n:latest

USER root

# Install docker-cli statically since apk might be missing in hardened images
RUN wget -q https://download.docker.com/linux/static/stable/x86_64/docker-26.1.4.tgz -O /tmp/docker.tgz && \
    tar -xz -C /tmp -f /tmp/docker.tgz && \
    mv /tmp/docker/docker /usr/local/bin/docker && \
    rm -rf /tmp/docker /tmp/docker.tgz

# Copy python3 and all required shared libraries from builder stage
COPY --from=python-builder /usr/bin/python3 /usr/bin/python3
COPY --from=python-builder /usr/bin/python3.12 /usr/bin/python3.12
COPY --from=python-builder /usr/lib/python3.12 /usr/lib/python3.12
COPY --from=python-builder /usr/lib/libpython3.12.so.1.0 /usr/lib/libpython3.12.so.1.0
COPY --from=python-builder /lib/ld-musl-x86_64.so.1 /lib/ld-musl-x86_64.so.1
COPY --from=python-builder /usr/lib/libsqlite3.so.0 /usr/lib/libsqlite3.so.0
COPY --from=python-builder /usr/lib/libpq.so.5 /usr/lib/libpq.so.5
COPY --from=python-builder /usr/lib/libcrypto.so.3 /usr/lib/libcrypto.so.3
COPY --from=python-builder /usr/lib/libssl.so.3 /usr/lib/libssl.so.3

# Run as root so docker socket is accessible (local dev environment)
# USER node  ← commented out intentionally
