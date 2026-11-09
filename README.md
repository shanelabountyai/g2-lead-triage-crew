# g2-lead-triage-crew — Lead Triage Crew (G2)

Build-log G2, Agentic AI track. A new HubSpot lead triggers an **orchestrator** that decides which specialists to call — an **Enricher**, a **Qualifier**, a **Drafter** — writes its findings back to HubSpot as a note, and leaves a follow-up email as a draft in a second note. **It never sends anything**, and in the code version that is enforced by the system (a hook and an interface with no send method), not promised by a prompt.

It is built twice: **G2·C** in Python with the Claude Agent SDK (this README; built first, unattended, D-1) and **G2·B** in n8n (the owner's hand build afterwards, from the same synthetic leads and the same contracts). Both attach to the shared capability layer **G0** (`shanelabountyai/g0-shared-layer`) instead of carrying their own rules.

Spec: `docs/prd.md`. Every decision is numbered in `docs/DECISIONS.md` (D-1..D-10 the owner's, D-11..D-19 this build's). Backlog: `docs/BACKLOG.md`. Eval: `docs/eval-report.md`. State and the owner's hand steps: `NEXT.md`.

## G2·C (code) — for a reviewer

### Architecture

```
HubSpot contact.creation ──▶ POST /hubspot/webhook (FastAPI, v3 signature)      triage replay ──┘ (local)
                                      │
                                      ▼
   Crew.run_lead(lead)  ── health first; one run_id per replay; $10 cap ──────────────────────────────────────
     1  duplicate check (code: +tag email or same name+company, older contact)  → band duplicate, no workers
     2  Orchestrator agent   [tools: find_duplicates]            → plan: enricher? qualifier? + reasons
     3  Enricher agent       [tools: lookup_company]             → company fields; the DIRECTORY overrides the model
        (skipped when the contact already has company+industry+size+website)
     4  Qualifier agent      [tools: evaluate_fit]               → role, relationship, reasons;
        score = G0 evaluation(rubric g2_lead_fit_v1) in code     → band (precedence D-13)
     5  Drafter agent        [tools: check_consent, check_brand, check_claims]
        only if band == good fit AND G0 audience_consent.allowed → draft; G0 brand_policy + claims_registry run on it in code
     6  triage note (+ draft note) → G0 measurement lead.triaged
   every model call, every skip, every blocked tool attempt → G0 observability
```

Each agent is **one Claude Agent SDK session** (`claude_agent_sdk.query`) with its own system prompt and context, `tools=[]` (no built-ins), `allowed_tools` = the short list above served by an **in-process SDK MCP server** (`src/triage/tools.py`), `permission_mode="dontAsk"`, a JSON-schema `output_format`, `max_budget_usd`, and the **PreToolUse hook** `safety.make_block_hook` that denies anything shaped like a send, an email-out or a deal-stage edit and logs it (D-7, D-11). The governance calls happen **in code after each worker regardless of what the model did** (D-11): the model may look (its tools), the crew decides.

Files: `src/triage/` — `crew.py` (the order above, the hard rules, the notes), `workers.py` (the three workers, `run_agent`, the enforcement), `prompts.py` (agent specs: model, effort, schema, tool list), `tools.py` (the six tools), `llm.py` (`AgentSdkCaller`, `RecordedCaller`, `RecordingCaller`), `layer.py` (G0 adapter), `hubspot.py` (interface, fake, real), `safety.py` (hook, synthetic-only guard), `bands.py` (band precedence, duplicate rule), `directory.py` (synthetic companies), `webhook.py`, `cli.py`, `evalreport.py`, `models.py`.

### How each G0 capability is called

| Capability | Where | What it decides |
|---|---|---|
| `health` | `Crew.__init__` → `layer.require_healthy()` | A degraded layer, or a missing `g2_lead_fit_v1`, stops the run before any lead. |
| `audience.consent` | `crew.py` step 5, before the Drafter is called; also the Drafter's own `check_consent` tool | No consent on `email` (not_consented, do_not_contact, unknown_contact) → no draft; the note says why (D-15). |
| `brand.policy` | `workers.enforce_draft` on subject + body (channel `email`); also the Drafter's `check_brand` tool | Violations travel with the draft note (rule id, excerpt, fix). The never-use list lives in G0, not in the prompt. |
| `claims.registry` | `workers.enforce_draft` on the body; also the Drafter's `check_claims` tool | Any `unsupported` / `needs_source` sentence is listed on the draft note. |
| `evaluation` | `workers.enforce_qualification` with rubric **`g2_lead_fit_v1`** (`rubrics/lead_fit_v1.json`, loaded through G0's seed loader, D-2); also the Qualifier's `evaluate_fit` tool | Score = `total × 100`; `passed` (threshold 0.8 + required criteria) decides good fit vs poor fit. Judge `deterministic` by default, `--judge claude` opts in (logged and capped by G0). |
| `observability` | `workers.run_agent` after every model call (`agent`, `step=<lead>:<agent>`, billed tokens, cost from G0's price table); `crew._skip` for every skip (`status=skipped`); the hook's `on_block` for every blocked attempt (`status=error`) | `over_cap` stops further model calls; this repo has no price table of its own (D-10). |
| `measurement` | `crew.py` step 6, after the note write succeeded | `lead.triaged` with band, score, workers called/skipped, drafted, cost — never a name or email. |

The rubric's buyer definition comes from `li-lead-gen-tools` (D-5): D-1 "any leader sponsoring an AI pilot", `DECISION_ROLES` (executive-sponsor, pilot-lead) and the Stalled-Pilot Diagnostic's `leadGrade` conditions, plus the triage-specific criteria (a buyer, not a vendor / student / advisor; a company that can be identified; size).

### Safety, enforced not promised

- **Nothing is ever sent.** The HubSpot interface (`hubspot.HubSpotClient`) has four methods: `get_contact`, `find_contacts`, `create_note`, `list_notes`. No send, no deal method — `tests/test_hubspot.py` pins it. No agent has a send tool. The hook denies any tool whose name or input looks like a send (`send_email`, `gmail_send`, `smtp`, HubSpot single-send / transactional URLs, a recipient+body payload…) or a deal-stage edit, and logs the attempt to the safety log and to `observability` (PRD AC 4: `tests/test_safety.py`, and end to end `tests/test_crew.py::test_ac4_forced_send_from_a_worker_is_blocked_and_logged`, where a recorded Drafter "tries" `mcp__hubspot__send_email` and a `curl` to the transactional endpoint — both blocked, both logged, the draft still lands as a note).
- **Notes on synthetic test contacts only.** `safety.assert_synthetic` refuses any email not on `@example.com`; both the fake and the real client call it before every write.
- **Every tool outside an agent's list is denied** by the same hook (an Enricher that reaches for `check_consent` is blocked and logged).
- **The real HubSpot client was never exercised** in this build (no token; the kickoff forbids live HubSpot calls). It is implemented against v3 contacts/notes and request-shape tested with a mock transport.

### How to run on fixtures (no key, no network)

```bash
uv sync --all-groups                     # Python 3.12 venv; pins g0-shared-layer at commit 1cb74df (D-2)
uv run pytest                            # 79 tests, ~2 s, no network, no model
uv run triage run --fixtures             # 20 leads through the crew on the recorded fake → out/<run_id>/{run-log.json,notes.md,eval-report.md}
uv run triage eval --run-log out/<run_id>/run-log.json
uv run triage serve                      # the webhook on :8042 (fake HubSpot seeded from fixtures/leads.json; real client with HUBSPOT_PRIVATE_APP_TOKEN, D-20)
uv run triage replay                     # in another shell: posts one contact.creation event per fixture lead
```

Without `ANTHROPIC_API_KEY` the crew runs on **`fixtures/recorded-responses.json`**, one answer per agent per lead. **That file is hand-made by `fixtures/make-recorded.py` from the lead fields with plain heuristics — it never reads the labels, and it is not a recording of a live model** (D-16). Its usage is zero, so every cost line says "not measured live". State lives in `G0_DB_PATH` (the layer's SQLite; default `~/.g0-shared-layer/layer.sqlite`); point it at a scratch file to replay from a clean slate.

### How to run live

```bash
cp .env.example .env                                   # fill ANTHROPIC_API_KEY (and G0_DB_PATH); never committed
uv run triage run --fixtures --record                  # live model calls through the SDK; overwrites recorded-responses.json with real responses
uv run triage run --fixtures --judge claude            # optional: G0's Claude judge for the rubric (logged, capped)
```

Models: Orchestrator / Qualifier / Drafter `claude-sonnet-5-5`, Enricher `claude-haiku-5-5` (ids and prices confirmed on 2026-11-06 from Anthropic's docs and identical to G0's table, D-10). Hard cap **$10** per run (`G0_RUN_CAP_USD`, plus `max_budget_usd` on every session); the crew stops at `over_cap`. A live run against the owner's HubSpot (token + webhook subscription) is a hand step with its own go — `NEXT.md`.

### Eval results

`docs/eval-report.md` (AC 5). This build: **band accuracy 20/20 in fixture mode** (good fit 8/8, poor fit 4/4, student 2/2, vendor 2/2, duplicate 2/2, missing company info 2/2) — **not measured live**; the number tests the governed pipeline (duplicates, directory, rubric, consent gate, band precedence) with a fake that never saw the labels. **Cost per lead: not measured live** ($0.00; no key present). 26 notes written: 20 triage notes, 6 draft notes (the 8 good fits minus the two without email consent, D-15). 21 worker skips logged with reasons; 0 blocked attempts in the run (the forced-send case is a test). `docs/sample-run-notes.md` has every note from the run.

### What is honest to say is not done

- No live G2·C model call has happened; the recorded fixture is hand-made and labelled as such. `triage run --fixtures --record` with a key replaces it (hand step H2).
- The real HubSpot client has never talked to HubSpot; loading the 20 synthetic contacts and the live note write-back are hand steps (H3, H4).
- The Enricher is synthetic-only by decision (D-6); live web lookup is the owner's call.
- G0's evaluation contract has no rubric-registration tool, so the rubric is loaded through G0's seed loader in-process (D-2) — the one place this consumer writes to the layer's store other than through a tool. A `rubric.register` v1.1 tool is proposed in `NEXT.md`.
- Single process, stdio-free (G0 is called in-process, as G1·C does); no auth on the webhook beyond HubSpot's v3 signature, which is required whenever HubSpot or the model is live (unsigned only in fixture/fake mode, D-21); the webhook dedupes HubSpot retries in memory (D-22).

## Layout

```
KICKOFF.md, KICKOFF-G2C.md      the two kickoffs (G2·C's is the one that ran)
docs/{prd,DECISIONS,BACKLOG,eval-report,sample-run-notes}.md
rubrics/lead_fit_v1.json        the Qualifier rubric (loaded into G0 evaluation as g2_lead_fit_v1)
fixtures/                       leads.json (20, labeled), companies.json, recorded-responses.json, make-recorded.py, README.md
src/triage/                     the crew (see Files above)
tests/                          79 tests: fixtures, safety, layer, hubspot, directory, workers, crew (AC 1–5), webhook/CLI
```
