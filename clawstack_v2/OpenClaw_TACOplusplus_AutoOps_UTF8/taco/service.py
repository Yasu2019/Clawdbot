import os
from fastapi import FastAPI
from pydantic import BaseModel
from taco.controller import TacoController

app = FastAPI(title='OpenClaw TACO++ AutoOps')
controller = TacoController(os.getenv('TACO_CONFIG','taco/config.yaml'))

class CompressReq(BaseModel):
    text: str
    domain: str = 'generic'

@app.get('/health')
def health(): return {'ok': True, 'service': 'taco++'}

@app.post('/compress')
def compress(req: CompressReq):
    return controller.process(req.text, req.domain)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8765)
