const express = require('express');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.static('public'));

const WORKSPACES_DIR = '/root/.shannon/workspaces';
const TARGET_URL     = process.env.TARGET_URL   || 'http://host.docker.internal:5001';
const TARGET_REPO    = process.env.TARGET_REPO  || '/repos/target';
const CONFIG_FILE    = process.env.CONFIG_FILE  || '/repos/target/shannon-config.yaml';

let scanProcess  = null;
let scanStatus   = 'idle';   // idle | running | completed | failed
let currentWs    = null;
let scanCost     = 0;
let sseClients   = [];

// ── SSE log stream ──────────────────────────────────────────────────────────
app.get('/api/logs/stream', (req, res) => {
  res.set({ 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  sseClients.push(res);
  req.on('close', () => { sseClients = sseClients.filter(c => c !== res); });
  res.write(`data: ${JSON.stringify({ type: 'system', line: 'Connected to log stream' })}\n\n`);
});

function broadcast(type, line) {
  const msg = `data: ${JSON.stringify({ type, line })}\n\n`;
  sseClients.forEach(c => c.write(msg));
}

// ── Status ──────────────────────────────────────────────────────────────────
app.get('/api/status', (req, res) => {
  // Read cost from workflow.log if running
  if (currentWs) {
    const wlog = path.join(WORKSPACES_DIR, currentWs, 'workflow.log');
    if (fs.existsSync(wlog)) {
      const tail = fs.readFileSync(wlog, 'utf8').split('\n').slice(-20).join('\n');
      const m = tail.match(/Total Cost:\s+\$([0-9.]+)/);
      if (m) scanCost = parseFloat(m[1]);
    }
  }
  res.json({ status: scanStatus, workspace: currentWs, cost: scanCost, target: TARGET_URL });
});

// ── Report ──────────────────────────────────────────────────────────────────
app.get('/api/report', (req, res) => {
  if (!currentWs) return res.json({ report: null });
  const rpt = path.join(WORKSPACES_DIR, currentWs, 'deliverables', 'comprehensive_security_assessment_report.md');
  if (fs.existsSync(rpt) && fs.statSync(rpt).size > 50) {
    return res.json({ report: fs.readFileSync(rpt, 'utf8') });
  }
  // Fallback: collect available partial deliverables
  const dir = path.join(WORKSPACES_DIR, currentWs, 'deliverables');
  if (fs.existsSync(dir)) {
    const parts = fs.readdirSync(dir)
      .filter(f => f.endsWith('.md') && f !== 'comprehensive_security_assessment_report.md')
      .map(f => `## ${f}\n\n` + fs.readFileSync(path.join(dir, f), 'utf8'));
    if (parts.length) return res.json({ report: parts.join('\n\n---\n\n'), partial: true });
  }
  res.json({ report: null });
});

// ── Start ───────────────────────────────────────────────────────────────────
app.post('/api/start', (req, res) => {
  if (scanStatus === 'running') return res.status(400).json({ error: 'Scan already running' });

  const model = req.body.model || 'openrouter,anthropic/claude-sonnet-4-5';
  scanStatus = 'running';
  scanCost   = 0;
  currentWs  = null;

  const env = {
    ...process.env,
    OPENROUTER_API_KEY:          process.env.OPENROUTER_API_KEY,
    ROUTER_DEFAULT:              model,
    CLAUDE_CODE_MAX_OUTPUT_TOKENS: '64000',
    HOME: '/root',
  };

  const args = ['@keygraph/shannon', 'start',
    '-u', TARGET_URL,
    '-r', TARGET_REPO,
    '-c', CONFIG_FILE,
    '--router'
  ];

  broadcast('system', `Starting Shannon [model: ${model}] → ${TARGET_URL}`);
  scanProcess = spawn('npx', args, { env, stdio: ['pipe', 'pipe', 'pipe'] });

  function parseLine(line) {
    // strip ANSI
    line = line.replace(/\x1b\[[0-9;]*[mK]/g, '').trim();
    if (!line) return;
    broadcast('log', line);
    const wsM = line.match(/Workspace:\s+(\S+)/);
    if (wsM) currentWs = wsM[1];
    const costM = line.match(/Total Cost:\s+\$([0-9.]+)/);
    if (costM) scanCost = parseFloat(costM[1]);
  }

  scanProcess.stdout.on('data', d => d.toString().split('\n').forEach(parseLine));
  scanProcess.stderr.on('data', d => d.toString().split('\n').forEach(l => {
    l = l.replace(/\x1b\[[0-9;]*[mK]/g, '').trim();
    if (l) broadcast('stderr', l);
  }));
  scanProcess.on('close', code => {
    scanStatus = code === 0 ? 'completed' : 'failed';
    broadcast('system', `Scan ${scanStatus}${scanCost ? ` | Total cost: $${scanCost.toFixed(4)}` : ''}`);
    scanProcess = null;
  });

  res.json({ status: 'started', model });
});

// ── Stop ────────────────────────────────────────────────────────────────────
app.post('/api/stop', (req, res) => {
  if (scanProcess) { scanProcess.kill('SIGTERM'); scanProcess = null; }
  try {
    execSync('npx @keygraph/shannon stop 2>/dev/null', {
      env: { ...process.env, HOME: '/root' },
      timeout: 15000
    });
  } catch (_) {}
  scanStatus = 'idle';
  broadcast('system', 'Scan stopped by user');
  res.json({ status: 'stopped' });
});

app.listen(5002, '0.0.0.0', () => console.log('Shannon Control on :5002'));
