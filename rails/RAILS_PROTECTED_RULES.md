# Rails Protected Rules

## Default Protected Areas
Do not touch these unless explicitly requested:
- app/views/layouts/*
- app/views/shared/*
- app/assets/stylesheets/*
- app/javascript/*
- config/routes.rb
- Gemfile / Gemfile.lock

## Rails AI Edit Policy
For normal bug fixes:
- Prefer model/service/controller single-file fixes.
- Do not change global layout.
- Do not change CSS/Tailwind classes.
- Do not change routes.
- Do not change database migrations unless requested.

## Before Editing Rails
Report:
- Controller/model/view involved
- Expected changed files
- Whether protected areas are involved
- Backup status
