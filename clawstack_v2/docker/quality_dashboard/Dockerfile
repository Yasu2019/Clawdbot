FROM python:3.11

# System deps for LaTeX and OpenGL
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-science \
    texlive-fonts-recommended \
    libgl1 \
    libglu1-mesa \
    libglib2.0-0 \
    build-essential \
    locales \
    libpng-dev \
    libjpeg-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Locale for IDTFConverter
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# Build IDTFConverter from source for U3D export
# Note: Use C++14 to avoid C++17 dynamic exception specification errors
RUN git clone https://github.com/ningfei/u3d.git /tmp/u3d \
    && cd /tmp/u3d \
    && CXXFLAGS="-std=c++14" ./configure && make && make install \
    && rm -rf /tmp/u3d

# Python dependencies
RUN pip install --no-cache-dir streamlit pandas numpy pypdf openpyxl python-docx python-pptx pymeshlab ezdxf trimesh gmsh scipy plotly streamlit-plotly-events

WORKDIR /app
COPY app.py /app/app.py
COPY .streamlit /app/.streamlit

EXPOSE 8090

CMD ["streamlit", "run", "app.py", "--server.port", "8090", "--server.address", "0.0.0.0"]
