import json, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path('/data/asana_quality')
DATA.mkdir(parents=True, exist_ok=True)
QUEUE = DATA / 'proposal_queue.jsonl'
APPROVED = DATA / 'approved_queue.jsonl'
REJECTED = DATA / 'rejected_queue.jsonl'
DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'
ASANA_TOKEN = os.getenv('ASANA_ACCESS_TOKEN', '')
DEFAULT_PROJECT = os.getenv('ASANA_DEFAULT_PROJECT_GID', '')

def read_jsonl(path):
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def append_jsonl(path, obj):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')

def asana_create_task(task):
    if DRY_RUN:
        return {'dry_run': True, 'task': task}
    if not ASANA_TOKEN:
        raise RuntimeError('ASANA_ACCESS_TOKEN is empty')
    payload = {
        'data': {
            'name': task.get('name', '品質タスク'),
            'notes': task.get('notes', ''),
            'projects': [task.get('project_gid') or DEFAULT_PROJECT],
            'due_on': task.get('due_on'),
        }
    }
    payload['data'] = {k:v for k,v in payload['data'].items() if v}
    req = urllib.request.Request(
        'https://app.asana.com/api/1.0/tasks',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {ASANA_TOKEN}', 'Content-Type':'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode('utf-8'))

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == '/health': return self._send(200, {'ok': True, 'dry_run': DRY_RUN})
        if self.path == '/proposals': return self._send(200, {'items': read_jsonl(QUEUE)})
        return self._send(404, {'error': 'not_found'})
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length) or b'{}')
        if self.path == '/propose':
            body['proposal_id'] = body.get('proposal_id') or f"q-{int(time.time()*1000)}"
            body['status'] = 'pending_approval'
            append_jsonl(QUEUE, body)
            return self._send(200, {'queued': True, 'proposal_id': body['proposal_id']})
        if self.path == '/approve':
            result = asana_create_task(body)
            body['status'] = 'approved'
            append_jsonl(APPROVED, {'proposal': body, 'asana_result': result})
            return self._send(200, {'approved': True, 'asana_result': result})
        if self.path == '/reject':
            body['status'] = 'rejected'
            append_jsonl(REJECTED, body)
            return self._send(200, {'rejected': True})
        return self._send(404, {'error': 'not_found'})

if __name__ == '__main__':
    HTTPServer(('0.0.0.0', 18920), Handler).serve_forever()
