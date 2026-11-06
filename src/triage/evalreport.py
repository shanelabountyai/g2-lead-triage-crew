"""AC 5: band accuracy against the hand labels, and cost per lead (D-10, D-16)."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from triage.crew import Crew
from triage.models import BANDS, LabeledLead, TriageResult


def accuracy(leads: list[LabeledLead], results: list[TriageResult]) -> tuple[int, int, list[tuple[str, str, str]]]:
    by = {r.lead_id: r for r in results}
    misses = []
    correct = 0
    for lead in leads:
        r = by.get(lead.id)
        if r is None:
            misses.append((lead.id, lead.label.band, "not processed"))
            continue
        if r.band == lead.label.band:
            correct += 1
        else:
            misses.append((lead.id, lead.label.band, r.band))
    return correct, len(leads), misses


def build_report(crew: Crew, leads: list[LabeledLead], results: list[TriageResult]) -> str:
    correct, total, misses = accuracy(leads, results)
    by = {r.lead_id: r for r in results}
    measured = bool(results) and all(r.measured for r in results)
    run_cost, layer_calls = crew.run_cost()
    per_lead = (run_cost / len(results)) if results else 0.0
    mode = "live (Claude Agent SDK)" if measured else f"fixture mode — recorded fake ({crew.caller.name}); usage is zero, so cost is **not measured live**"
    confusion: Counter[tuple[str, str]] = Counter((lead.label.band, by[lead.id].band) for lead in leads if lead.id in by)

    lines = [
        "# Eval report — G2·C",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} · run `{crew.run_id}` · mode: {mode} · judge: `{crew.judge}` · HubSpot: `{crew.hubspot.name}`.",
        "",
        "## Band accuracy vs the hand labels (AC 5)",
        "",
        f"**{correct} / {total} correct ({(100 * correct / total) if total else 0:.0f}%)** — " + ("measured live." if measured else "**fixture mode, not measured live**: the recorded fake answers from the lead fields, never the labels (D-16), so this number tests the governed pipeline (duplicates, directory, rubric, consent, band precedence), not a model."),
        "",
        "| label \\ got | " + " | ".join(BANDS) + " |",
        "|---|" + "---|" * len(BANDS),
    ]
    for lab in BANDS:
        lines.append(f"| {lab} | " + " | ".join(str(confusion.get((lab, got), 0) or "") for got in BANDS) + " |")
    if misses:
        lines += ["", "Misses:", ""] + [f"- {lid}: labeled `{lab}`, got `{got}`" for lid, lab, got in misses]
    lines += [
        "",
        "## Cost per lead (AC 5)",
        "",
        (f"**${per_lead:.4f} per lead**, ${run_cost:.4f} for {len(results)} leads, computed from the response usage with G0's price table (D-10)."
         if measured else f"**Not measured live.** {len(results)} leads, $0.0000 — no `ANTHROPIC_API_KEY` was present, so no model was called. The hand step in NEXT.md produces the live number."),
        f"Shared-layer calls this run: {layer_calls} observability rows (one per model call, per blocked attempt and per skip).",
        "",
        "## Per lead",
        "",
        "| lead | label | band | score | workers called | skipped (reason) | draft | cost | blocked |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for lead in leads:
        r = by.get(lead.id)
        if r is None:
            lines.append(f"| {lead.id} | {lead.label.band} | — | — | — | not processed | — | — | — |")
            continue
        called = ", ".join(d.worker for d in r.decisions if d.called) or "none"
        skipped = "; ".join(f"{d.worker} ({d.reason})" for d in r.decisions if not d.called) or "—"
        draft = "saved" if (r.draft and r.draft.created) else (f"no ({r.draft.reason})" if r.draft else "—")
        cost = f"${r.cost_usd:.4f}" if r.measured else "n/m"
        mark = "" if r.band == lead.label.band else " ✗"
        lines.append(f"| {lead.id} | {lead.label.band} | {r.band}{mark} | {r.score if r.score is not None else '—'} | {called} | {skipped} | {draft} | {cost} | {r.blocked_attempts} |")
    drafted = sum(1 for r in results if r.draft and r.draft.created)
    lines += [
        "",
        "## Acceptance criteria",
        "",
        f"1. Every lead gets a note with score, band and reasons: **{len(results)}/{len(leads)}** triage notes written ({len(crew.hubspot.notes)} notes in all).",
        f"2. Good-fit leads get a saved draft, nothing sent: **{drafted} drafts** saved as notes headed `DRAFT — not sent`; {sum(1 for r in results if r.band == 'good fit' and not (r.draft and r.draft.created))} good fits without a draft for lack of consent (D-15). No send path exists.",
        f"3. Orchestrator skipping a worker with the reason logged: **{sum(1 for r in results for d in r.decisions if not d.called)} skips** logged as observability rows (`status=skipped`) and listed in the notes.",
        f"4. Forced send blocked by the hook and logged: `tests/test_crew.py::test_ac4_forced_send_from_a_worker_is_blocked_and_logged` and `tests/test_safety.py`; blocked attempts in this run: **{len(crew.blocked)}**.",
        f"5. Band accuracy and cost per lead: above.",
        "",
    ]
    return "\n".join(lines)
