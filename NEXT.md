# NEXT

State (2026-11-06, end of the unattended G2·C run on Claude Fable 5.1): **G2·C built on branch `kickoff`**, one PR open against `main` ([#1](https://github.com/shanelabountyai/g2-lead-triage-crew/pull/1)), unmerged. **79 tests pass** (6 fixtures, 28 safety, 8 layer, 8 HubSpot, 2 directory, 13 workers, 7 crew, 7 webhook/CLI); none skipped, none failing. **Cost of live model calls this run: $0.00** — no `ANTHROPIC_API_KEY` was present, so no model was called; the crew ran on fixtures with the recorded-response fake (D-16). **No HubSpot call was made** (no token; the real client exists and was never exercised, D-8).

## Done (PRD acceptance criteria)

1. Every synthetic lead gets a note with score, band and reasons — 20/20 (`docs/sample-run-notes.md`).
2. Consented good-fit leads get a saved draft note headed `DRAFT — not sent`; nothing is sent — 6 drafts; 2 good fits without email consent get no draft and the note says why (D-15).
3. The orchestrator skips workers with the reason logged — 21 skips as `observability` rows and note lines (Enricher skipped for a complete profile, Qualifier + Drafter for an unresolvable company, Drafter for poor fit / student / vendor / no consent, everything for a duplicate).
4. A forced send attempt is blocked by the hook and logged — `tests/test_safety.py` (hook) and `tests/test_crew.py::test_ac4_…` (end to end: `mcp__hubspot__send_email` and a `curl` to HubSpot's transactional endpoint, both denied, both in `observability` and the safety log).
5. Band accuracy and cost per lead — `docs/eval-report.md`: **20/20 in fixture mode (not measured live)**; **cost per lead not measured live**.

Also: D-1..D-19 in `docs/DECISIONS.md`; G0 pinned at `1cb74df` and called in-process (health first); rubric `g2_lead_fit_v1` in `rubrics/`; webhook + replay; README for a reviewer.

## Stubbed or deferred (said plainly)

- **`fixtures/recorded-responses.json` is hand-made** by `fixtures/make-recorded.py` from the lead fields (never the labels) in each agent's output schema. It is not a recording of a live model. The 20/20 shows the governed pipeline works; it says nothing about a model's judgment yet.
- **`AgentSdkCaller` (the live path) has never run.** Its options are built and tested (`tools=[]`, allowed list, hook with `on_failure="block"`, structured output, budget), and the same hook and tool handlers are exercised by the recorded path, but the SDK session itself is untested live.
- **`RealHubSpot` has never talked to HubSpot.** Request shapes are tested with a mock transport; the synthetic-only write guard is tested.
- **G0 has no `rubric.register` tool**, so the rubric is loaded through G0's seed loader in-process (D-2). This is the one write to the layer's store not made through a tool. Proposed for G0 v1.1.
- **Enricher is synthetic-only** (D-6). Live web lookup is your call.
- The webhook has no auth beyond HubSpot's v3 signature (required whenever HubSpot or the model is live; `triage serve` refuses to start without `HUBSPOT_CLIENT_SECRET` then, D-21). Retry dedupe is in memory and lost on restart (D-22).

## Owner's hand steps

1. **H1 — Review the `kickoff` PR.** Merge only on your own say-so. When G0's `v0.1.0` tag exists, move the pin in `pyproject.toml` from the commit to the tag.
2. **H2 — First live run (fixtures, no HubSpot).** `cp .env.example .env`, set `ANTHROPIC_API_KEY` (and `G0_DB_PATH` to a scratch file), then `uv run triage run --fixtures --record --report docs/eval-report.md`. This makes the live model calls (cap $10, D-10), overwrites `fixtures/recorded-responses.json` with real responses, and rewrites the eval report with **live band accuracy and cost per lead**. Commit both. Optional: `--judge claude` to let G0's Claude judge score the rubric.
3. **H3 — Load the 20 synthetic leads into HubSpot.** `uv run triage hubspot-load` writes `fixtures/hubspot-batch-create.json` (gitignored) and prints the one `curl` to run from your machine with `HUBSPOT_PRIVATE_APP_TOKEN` (the `li-lead-gen-tools` private app has the `li_tool_*` properties; `message` is dropped unless you create that property). Every email is on `example.com`. Note the contact ids HubSpot assigns; the fake uses `hs-1001…hs-1020`, HubSpot will not.
4. **H4 — Live run against HubSpot (your go).** Set `HUBSPOT_PRIVATE_APP_TOKEN` and `HUBSPOT_CLIENT_SECRET`, `uv run triage serve --public-url https://<tunnel>`, create a HubSpot webhook subscription on `contact.creation` pointing at `https://<tunnel>/hubspot/webhook`, then either create a test contact in the portal or `uv run triage replay <hubspot contact ids>`. Notes land on the synthetic contacts only (`safety.assert_synthetic` refuses anything else); nothing is sent.
5. **H5 — G2·B, the n8n build by hand** (`docs/prd.md` "G2·B build notes"), from the same `fixtures/leads.json` and the same G0 contracts: HubSpot trigger → orchestrator AI Agent node → Enricher / Qualifier / Drafter as AI Agent Tool nodes → HubSpot note nodes; **no send node anywhere**. Score with G0·B's `evaluation` sub-workflow on the `g2_lead_fit_v1` criteria (`rubrics/lead_fit_v1.json`); consent, brand and claims through the G0·B sub-workflows. Then compare band accuracy and cost per lead with `docs/eval-report.md` (AC 5, both versions).
6. **H6 — Two decisions:** (a) may the Enricher use live web lookup for the public demo (D-6)? (b) should G0 get a `rubric.register` tool (a v1.1 contract) so this repo stops seeding its rubric through the loader (D-2)?

## Next items

- Live eval numbers (H2) and the G2·B side of the AC 5 comparison (H5).
- LinkedIn write-up (PRD question 3) after the live numbers exist.
- G3–G5 attach the same way: `layer.py`, `tools.py` and `safety.py` are reusable as they are.
