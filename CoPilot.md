CoPilot Handover Notes
======================

Date: 2026-02-27

Overview
--------
This note documents the LearnPress installation and detection work performed in the MCP server and frontend, what was validated by tests, the debugging and container work done to get tests passing in the production docker-compose environment, and recommended next steps and suggestions.

What was implemented (high-level)
---------------------------------
- Detection: GraphQL introspection (look for LearnPress types like "course"/"learnpress") plus REST discovery against common LearnPress namespaces (learnpress/v1, lp/v1).
- Install flow: best-effort attempts in order—GraphQL mutation (speculative) → REST install endpoint (best-effort) → SSH/wp-cli fallback using scripts/setup-remote-wordpress.py.
- Input hardening: plugin_slug sanitization to ^[a-z0-9_-]+$ to avoid path traversal and unsafe input.
- Frontend: Next.js API wrappers added (web/src/app/api/...) and an "Install LearnPress" button wired to the MCP install endpoint.

What was done during testing and debugging (this session)
--------------------------------------------------------
- Added unit tests: mcp-server/tests/test_learnpress.py covering GraphQL detection, invalid plugin slug, and SSH fallback behavior.
- Observed a failing test (test_install_learnpress_ssh_fallback returning HTTP 500).
- Added an auxiliary debug test (mcp-server/tests/test_learnpress_debug.py) to capture and print response bodies when running inside the container.
- Root cause during container runs: the server could not find the setup script (scripts/setup-remote-wordpress.py) at the resolved path, causing the SSH fallback to return "Setup script not found" (500).
- Fixed Docker image so the scripts are present inside the container: updated docker/mcp-server/Dockerfile to COPY scripts/ into /app/scripts and also to /scripts so module-level relative lookup succeeds.
- Rebuilt the mcp-server image using docker-compose.production.yml and re-ran the tests inside the articulate-mcp container; verified the failing SSH-fallback test now passes and overall tests report "3 passed".

Repro steps (what was run)
-------------------------
1. Rebuild and start the production-like mcp-server service:
   COMPOSE_FILE=docker-compose.production.yml
   docker compose -f $COMPOSE_FILE build --no-cache mcp-server
   docker compose -f $COMPOSE_FILE up -d --no-deps mcp-server

2. Run tests inside the running container and view server logs:
   docker exec -u 0 articulate-mcp sh -lc "pytest -q -s tests/test_learnpress.py || true"
   docker logs articulate-mcp --tail 400

Key files changed in this work
-----------------------------
- mcp-server/src/articulate_mcp/routes/learnpress.py  (new endpoints + install flow + sanitization)
- mcp-server/tests/test_learnpress.py  (unit tests)
- mcp-server/tests/test_learnpress_debug.py  (temporary debug helper to print outputs)
- docker/mcp-server/Dockerfile  (now copies scripts/ into the image and /scripts for reliable lookup)
- scripts/setup-remote-wordpress.py  (extended to accept --plugins; used by SSH fallback)
- web/src/app/api/... (Next.js API wrappers) and web/src/app/connections/page.tsx (UI button wiring)

Remaining/planned work (kept from previous plan)
------------------------------------------------
1. Fix and harden tests and mocks to be robust across import paths (monkeypatch the exact asyncio reference used by the module under test).  This reduces flakiness when tests run inside containers vs locally.
2. Improve endpoint error structure: return consistent JSON errors with machine-readable codes and human-friendly details.
3. Add more unit tests for REST/GraphQL failure modes, and tests asserting the plugin_slug sanitization rules.
4. Implement a mu-plugin push fallback (upload a mu-plugin that bootstraps plugin install) as an alternate for environments without WP-CLI.
5. E2E validation: run the complete install flow against a dev WP instance with WP-CLI present; document prerequisites.
6. UI improvements: surface progress logs, show install status, and provide actionable error messages to users.

My additional suggestions (prioritized)
--------------------------------------
1. Strengthen test isolation: instead of monkeypatching asyncio globally, mock the create_subprocess_exec at the module attribute (lp_route.asyncio.create_subprocess_exec) or wrap subprocess invocation in a small helper that can be cleanly monkeypatched. Add tests that assert temporary key file handling and cleanup.
2. Add structured logging and attach correlation IDs to install attempts so frontend and backend logs can be correlated when debugging remote installs.
3. Use a CI job that builds the mcp-server image and runs the pytest suite inside that image (mirrors local dev steps). This prevents the "works locally but fails in container" situations.
4. For local development and E2E: prefer running WP-CLI inside the WordPress container (docker exec) for installs during CI/dev rather than SSHing into the host; this is faster, more reproducible, and avoids uploading keys in tests.
5. Secrets & audit: ensure SSH private keys or passwords are kept only in transient NamedTemporaryFile entries and removed after use; consider encrypting long-lived credentials in the database and include audit records for remote installs (who triggered, when, outcome).
6. UX: make the frontend show streamed logs (SSE or websockets) from the install endpoint or worker task so users can see progress instead of a silent success/failure.

Actionable next steps (recommended immediate tasks)
-------------------------------------------------
- Make the subprocess invocation easier to mock (small wrapper function) and update tests to monkeypatch that wrapper; run the suite inside the container as part of CI.
- Add structured error codes to the install/check endpoints and update frontend handlers to surface those codes clearly.
- Implement the mu-plugin fallback and add unit tests for that path (simulate a WP without WP-CLI).
- Create an E2E job (or documented playbook) that runs the full install flow against a disposable WP instance with WP-CLI available; record the steps required and expected outputs.

Hand-off notes for Claude
------------------------
- The detection and install order is implemented; GraphQL install is speculative and may rarely work; REST install is best-effort; SSH/wp-cli fallback is the reliable path and is now covered by unit tests.
- The most recent failing test was due to the setup script not being available in the container; the Dockerfile was updated to copy scripts into the image and tests were re-run in-container to validate the fix.
- Provide guidance on implementing the mu-plugin fallback and adding streamed install logs for the UI.

If you want, next actions I can take now:
- Convert the subprocess call into a small, easily-mocked helper and update tests accordingly, then re-run tests inside the container and push the change.
- Implement structured error responses across the LearnPress endpoints and update the frontend to display them.

