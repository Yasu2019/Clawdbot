FROM julia:1.12.6-bookworm

WORKDIR /app

COPY Project.toml /app/Project.toml
COPY src /app/src

RUN julia --project=/app -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'

ENV JULIA_WORKER_HOST=0.0.0.0
ENV JULIA_WORKER_PORT=8096
ENV JULIA_NUM_THREADS=auto

EXPOSE 8096

CMD ["julia", "--project=/app", "/app/src/server.jl"]
