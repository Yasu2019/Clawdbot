# Protected Paths

## Rails Critical
- app/views/layouts/*
- app/views/shared/*
- app/assets/*
- app/javascript/*
- config/routes.rb

## Configuration Critical
- docker-compose.yml
- compose.yml
- .env
- .env.*
- config/database.yml
- config/credentials.yml.enc
- config/master.key

## OpenClaw Critical
- SOUL.md
- PROMISES.md
- TOOLS.md
- PORTAL_APPS.md
- docker-compose*.yml

## Rule
Protected files require explicit user instruction and GitHub backup before modification.
