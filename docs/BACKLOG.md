# Backlog — G2·C (code first, D-1)

Each item is one commit on branch `kickoff`, finishable and testable in one sitting, with its acceptance criteria taken from `docs/prd.md`. Status is updated as the run goes. Owner hand steps are listed separately at the end and mirrored in `NEXT.md`.

| # | Item | Acceptance | Status |
|---|---|---|---|
| C0 | `docs/DECISIONS.md` D-1..D-19, this backlog, `pyproject.toml` with the G0 pin (D-2), `.env.example` (names only) | Decisions recorded before any code; `uv sync` resolves the pinned commit | done |
| C1 | Fixtures: `fixtures/leads.json` (20 labeled leads), `fixtures/companies.json` (synthetic directory), `fixtures/README.md` | Six bands all present; every email `@example.com`; labels load as the eval set; a test pins both | done |
| C2 | Safety invariants + hook: `safety.py` (`block_send_hook`, `assert_synthetic`, safety log), `tests/test_safety.py` | A forced `send_email` / `gmail_send` / HubSpot single-send tool call is denied by the hook and logged (AC 4); a write to a non-example.com contact is refused; the HubSpot interface has no send or deal method | done |
| C3 | G0 attachment: `layer.py` adapter (in-process, D-12 of G1·C), `rubrics/lead_fit_v1.json` loaded as `g2_lead_fit_v1` (D-2), `hubspot.py` interface + `FakeHubSpot` + `RealHubSpot` (never exercised, D-8) | `health` first; `evaluation` scores a sample profile through the rubric; consent fails closed; fake notes round-trip; real client builds requests but makes no call in tests | done |
| C4 | Subagents: `prompts.py` (specs, schemas, limited tool lists), `tools.py` (SDK MCP server), `llm.py` (`AgentSdkCaller`, `RecordedCaller`, `RecordingCaller`), Enricher → Qualifier → Drafter workers in `workers.py` | Each worker has its own context and tool list; Enricher resolves from the directory only; Qualifier's score comes from G0 `evaluation`; Drafter runs only with consent (gated); its output is annotated by the brand and claims checks (saved with any violations listed, D-2) | done |
| C5 | Orchestrator: plan in `workers.plan` (agent spec in `prompts.py`) + hard rules in `crew.py` (D-12), `bands.py` (D-13), duplicates (D-14), `crew.py` end to end, `fixtures/make-recorded.py` + `fixtures/recorded-responses.json` (D-16) | AC 1: every lead gets a note with score, band, reasons; AC 2: consented good fits get a draft note, nothing sent; AC 3: a test shows a worker skipped with the reason logged | done |
| C6 | Webhook + replay: `webhook.py` (FastAPI, D-18), `cli.py` (`triage serve`, `triage replay`, `triage run --fixtures`, `triage eval`) | `POST /hubspot/webhook` with a fixture event runs the crew and writes the note; replay posts all 20; bad signature → 401 when a secret is set | done |
| C7 | Eval report + docs: `docs/eval-report.md` (band accuracy vs labels, cost per lead, fixture-mode vs live), `README.md` for a reviewer, `NEXT.md` | AC 5 reported (live numbers "not measured" without a key); all tests pass; PR opened against `main`, not merged | done |

## Owner hand steps (not in the backlog; see `NEXT.md`)

- H1 Review the `kickoff` PR; merge only on your own say-so.
- H2 Set `ANTHROPIC_API_KEY` and run `triage run --fixtures --record` once: live band accuracy and cost per lead, and a real recorded-responses file.
- H3 Load the 20 synthetic leads into HubSpot (`triage hubspot-load` writes the batch-create payload and prints the `curl` to run; it never calls HubSpot. The live write needs your go and a private-app token).
- H4 Run live against HubSpot (`HUBSPOT_PRIVATE_APP_TOKEN` and `HUBSPOT_CLIENT_SECRET` — serve refuses to start live without the secret, D-21 — a HubSpot webhook subscription on `contact.creation` pointing at `triage serve`).
- H5 G2·B: the n8n build by hand from the same fixtures and contracts (`docs/prd.md` "G2·B build notes").
- H6 Decide whether the Enricher may use live web lookup (D-6), and whether G0 gets a `rubric.register` tool (D-2).
