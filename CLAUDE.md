# CLAUDE.md

Guidance for AI coding agents working in this repository.

## gstack

This project uses [gstack](https://github.com/garrytan/gstack), an AI-agent skill
suite for Claude Code, installed at `~/.claude/skills/gstack`.

### Web browsing

- **Use the `/browse` skill from gstack for ALL web browsing.**
- **Never use `mcp__claude-in-chrome__*` tools.** All browser automation and web
  navigation must go through gstack's `/browse` skill.

### Available skills

Planning & review:
- `/office-hours` — product interrogation / requirements
- `/plan-ceo-review` — CEO-lens plan review
- `/plan-eng-review` — engineering-lens plan review
- `/plan-design-review` — design-lens plan review
- `/plan-devex-review` — developer-experience plan review
- `/autoplan` — automated planning
- `/design-consultation` — design consultation
- `/design-review` — design review
- `/devex-review` — developer-experience review

Building & design:
- `/design-shotgun` — visual design iteration
- `/design-html` — production HTML/markup generation

Quality & security:
- `/review` — code review
- `/qa` — automated QA (with browser)
- `/qa-only` — QA without other steps
- `/cso` — security audit
- `/canary` — canary checks
- `/benchmark` — benchmarking

Shipping & deploy:
- `/ship` — PR automation
- `/land-and-deploy` — production release
- `/setup-deploy` — deploy setup

Browser & web:
- `/browse` — web browsing / automation (use this for ALL browsing)
- `/connect-chrome` — connect to Chrome
- `/setup-browser-cookies` — configure browser cookies

Docs & knowledge:
- `/document-release` — document a release
- `/document-generate` — generate documentation
- `/retro` — retrospective
- `/investigate` — investigation
- `/learn` — capture learnings
- `/setup-gbrain` — set up persistent knowledge base

Control & workflow:
- `/careful` — careful mode
- `/freeze` — freeze changes
- `/guard` — guard changes
- `/unfreeze` — unfreeze changes
- `/codex` — Codex integration
- `/gstack-upgrade` — upgrade gstack
