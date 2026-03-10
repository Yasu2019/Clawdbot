FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg \
    tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng \
    fonts-ipafont-gothic && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download MediaPipe PoseLandmarker model (new Tasks API, replaces deprecated mp.solutions)
RUN python3 -c "\
import urllib.request; \
urllib.request.urlretrieve(\
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',\
  '/app/pose_landmarker_lite.task'\
); print('Model downloaded OK')"

COPY app/ ./

EXPOSE 7870

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7870"]
