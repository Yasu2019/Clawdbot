FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    tesseract-ocr \
    libgl1 \
    libglu1-mesa \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libxcursor1 \
    libxfixes3 \
    libxft2 \
    libfontconfig1 \
    libxinerama1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    streamlit \
    ezdxf \
    trimesh \
    plotly \
    numpy \
    shapely \
    matplotlib \
    mapbox-earcut \
    manifold3d \
    requests \
    gmsh \
    pandas \
    scipy \
    PyMuPDF \
    olefile

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8002

CMD ["streamlit", "run", "app.py", \
     "--server.port", "8002", \
     "--server.address", "0.0.0.0", \
     "--server.maxUploadSize", "100"]
