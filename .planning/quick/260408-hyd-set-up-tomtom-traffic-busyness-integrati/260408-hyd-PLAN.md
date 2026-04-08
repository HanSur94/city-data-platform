---
phase: quick-260408-hyd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/config.py
  - docker-compose.yml
  - .env.example
autonomous: true
must_haves:
  truths:
    - "YAML values like ${TOMTOM_API_KEY} resolve to actual environment variable values at config load time"
    - "Backend service in Docker picks up .env file variables automatically"
    - "New contributors know which env vars to set via .env.example"
  artifacts:
    - path: "backend/app/config.py"
      provides: "Environment variable resolution in YAML config values"
      contains: "resolve_env_vars"
    - path: ".env.example"
      provides: "Template for required environment variables"
      contains: "TOMTOM_API_KEY"
    - path: "docker-compose.yml"
      provides: "Backend service loads .env file"
      contains: "env_file"
  key_links:
    - from: "backend/app/config.py"
      to: "os.environ"
      via: "resolve_env_vars replaces ${VAR} patterns with os.environ values"
      pattern: "\\$\\{[A-Z_]+\\}"
    - from: "docker-compose.yml"
      to: ".env"
      via: "env_file directive"
      pattern: "env_file.*\\.env"
---

<objective>
Add environment variable resolution to the town YAML config loader so that `${VAR}` patterns in YAML values (like `api_key: "${TOMTOM_API_KEY}"`) are replaced with actual environment variable values. Also wire up Docker Compose to load from `.env` and provide a `.env.example` template.

Purpose: The TomTom traffic connector is already built and configured in `towns/aalen.yaml`, but the config loader passes the literal string `"${TOMTOM_API_KEY}"` instead of resolving it. This blocks all TomTom API calls.
Output: Working env var resolution in config, `.env.example` template, Docker `.env` integration.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/config.py
@docker-compose.yml
@towns/aalen.yaml
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add env var resolution to config loader</name>
  <files>backend/app/config.py, backend/tests/test_config_env.py</files>
  <behavior>
    - resolve_env_vars("${TOMTOM_API_KEY}") with TOMTOM_API_KEY=abc123 in env returns "abc123"
    - resolve_env_vars("no-vars-here") returns "no-vars-here"
    - resolve_env_vars({"key": "${VAR}"}) recursively resolves dict values
    - resolve_env_vars(["${VAR}", "plain"]) recursively resolves list items
    - resolve_env_vars(42) returns 42 (non-string passthrough)
    - resolve_env_vars("prefix-${VAR}-suffix") returns "prefix-value-suffix" (mid-string substitution)
    - Missing env var raises KeyError with clear message naming the variable
  </behavior>
  <action>
    1. Add `import os, re` to config.py.
    2. Create `resolve_env_vars(value)` function that:
       - If value is a str: use `re.sub(r'\$\{([^}]+)\}', lambda m: os.environ[m.group(1)], value)`. Wrap the environ lookup to raise a clear KeyError: f"Environment variable '{var}' not set (referenced in town YAML config)".
       - If value is a dict: return `{k: resolve_env_vars(v) for k, v in value.items()}`
       - If value is a list: return `[resolve_env_vars(item) for item in value]`
       - Otherwise: return value unchanged (int, float, bool, None passthrough)
    3. In `load_town()`, after `raw = yaml.safe_load(...)`, add `raw = resolve_env_vars(raw)` before `Town.model_validate(raw)`.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform && python -m pytest backend/tests/test_config_env.py -x -v</automated>
  </verify>
  <done>resolve_env_vars correctly substitutes ${VAR} patterns from os.environ in strings, dicts, and lists. load_town() applies it before validation. All tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Create .env.example and wire Docker Compose</name>
  <files>.env.example, docker-compose.yml</files>
  <action>
    1. Create `.env.example` at project root with:
       ```
       # City Data Platform — Environment Variables
       # Copy to .env and fill in real values: cp .env.example .env

       # Database (defaults match docker-compose.yml — override for external DB)
       DATABASE_URL=postgresql+asyncpg://citydata:citydata@db:5432/citydata

       # TomTom Traffic API (get key at https://developer.tomtom.com/)
       TOMTOM_API_KEY=your-tomtom-api-key-here
       ```
    2. In `docker-compose.yml`, add `env_file: ./.env` to the `backend` service block, placed right after the `build: ./backend` line and before the existing `environment:` block. Keep the existing hardcoded `DATABASE_URL` and `TOWN` in `environment:` — the `.env` file values supplement (not replace) them, so `TOMTOM_API_KEY` flows through while DATABASE_URL stays pinned for Docker.
  </action>
  <verify>
    <automated>cd /Users/hannessuhr/Projects/city-data-platform && test -f .env.example && grep -q "TOMTOM_API_KEY" .env.example && grep -q "env_file" docker-compose.yml && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>.env.example exists with TOMTOM_API_KEY template. docker-compose.yml backend service has env_file directive so .env vars are available to the container.</done>
</task>

</tasks>

<verification>
1. Unit tests for resolve_env_vars pass
2. .env.example contains TOMTOM_API_KEY placeholder
3. docker-compose.yml backend service includes env_file: ./.env
4. Existing config loading still works (Town model validation unchanged)
</verification>

<success_criteria>
- `python -m pytest backend/tests/test_config_env.py -x` passes
- `${TOMTOM_API_KEY}` in aalen.yaml resolves to actual env var value when TOMTOM_API_KEY is set
- `.env.example` documents all required env vars
- Docker backend service loads `.env` file
</success_criteria>

<output>
After completion, create `.planning/quick/260408-hyd-set-up-tomtom-traffic-busyness-integrati/260408-hyd-SUMMARY.md`
</output>
