# Clawdbot (Docker) template

## 1) Put secrets in `.env`
Copy `.env.example` to `.env` and fill:
- `CLAWDBOT_GATEWAY_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`

## 2) Start
```bash
docker compose up -d --build
```

Open:
- http://127.0.0.1:18789/

## 3) Logs
```bash
docker compose logs -f clawdbot-gateway
```

## 4) Run CLI commands
```bash
docker compose run --rm --profile cli clawdbot-cli models list
```

## 5) Stop
```bash
docker compose down
```
