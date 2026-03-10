from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import subprocess
from pathlib import Path
import uuid

app = FastAPI(title="3D PDF Conversion API")

# Path to the existing model2pdf.py
CONVERTER_SCRIPT = "/home/node/clawd/scripts/model2pdf.py"
TEMP_DIR = Path("/tmp/3d_pdf_jobs")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/convert")
async def convert_to_3d_pdf(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir()
    
    input_path = job_dir / file.filename
    output_pdf = job_dir / f"{input_path.stem}.pdf"
    
    try:
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run the converter script
        # Command: python3 model2pdf.py input.stl output.pdf
        result = subprocess.run(
            ["python3", CONVERTER_SCRIPT, str(input_path), str(output_pdf)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Conversion failed: {result.stderr}")
            
        if not output_pdf.exists():
            raise HTTPException(status_code=500, detail="PDF was not generated.")
            
        return FileResponse(
            path=output_pdf,
            filename=output_pdf.name,
            media_type="application/pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Note: In a production app, we'd want a cleanup task for TEMP_DIR

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
