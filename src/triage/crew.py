"""The crew: one lead in, one triage note (and maybe one draft note) out (D-11, D-12).

Order per lead, and the hard rules no plan may override:
  1. health (once per run) → 2. duplicate check in code → duplicate: note, no workers
  3. Orchestrator agent: plan (enricher? qualifier? reasons)
  4. Enricher (unless the contact's profile is complete, D-19) → unresolved company: skip Qualifier and Drafter
  5. Qualifier → G0 evaluation → score, band
  6. Drafter only for band `good fit` AND audience_consent.allowed → brand + claims checks → draft note
  7. triage note write → measurement `lead.triaged` (only after the write succeeded)
Every skip is an observability row with status `skipped` and the reason, and a line in the note (AC 3).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from triage.bands import decide_band, find_duplicate
from triage.directory import Directory
from triage.hubspot import FakeHubSpot, HubSpotClient
from triage.layer import Layer
from triage.llm import ModelCaller, RecordedCaller
from triage.models import DraftOutcome, Enrichment, Lead, Qualification, TriageResult, WorkerDecision, load_leads
from triage.notes import draft_note, triage_note
from triage.safety import BlockedAttempt, SafetyLog
from triage.tools import CrewContext, ToolHandlers
from triage.workers import OverCap, draft, enforce_enrichment, enrich, plan, profile_from_contact, qualify


def new_run_id(prefix: str = "g2c") -> str:
    return datetime.now(UTC).strftime(f"{prefix}-%Y%m%d-%H%M%S")


class Crew:
    def __init__(self, *, layer: Layer, hubspot: HubSpotClient, caller: ModelCaller, directory: Directory | None = None,
                 run_id: str | None = None, judge: str = "deterministic", safety_log: SafetyLog | None = None) -> None:
        self.layer = layer
        self.hubspot = hubspot
        self.caller = caller
        self.directory = directory or Directory()
        self.run_id = run_id or new_run_id()
        self.judge = judge
        self.safety_log = safety_log or SafetyLog()
        self.blocked: list[BlockedAttempt] = []
        self.over_cap = False
        self.handlers = ToolHandlers(CrewContext(layer=self.layer, directory=self.directory, hubspot=self.hubspot, run_id=self.run_id))
        self.results: list[TriageResult] = []
        self.layer.require_healthy()

    @classmethod
    def for_fixtures(cls, *, caller: ModelCaller | None = None, layer: Layer | None = None, run_id: str | None = None,
                     leads: list[Lead] | None = None, judge: str = "deterministic") -> Crew:
        """A crew on the fixtures: fake HubSpot seeded with the 20 leads, recorded responses unless a caller is given."""
        seeded = leads if leads is not None else list(load_leads())
        return cls(layer=layer or Layer(os.environ.get("G0_DB_PATH")), hubspot=FakeHubSpot.seeded(seeded),
                   caller=caller or RecordedCaller(), run_id=run_id, judge=judge)

    # -- helpers -------------------------------------------------------------------

    def _skip(self, lead: Lead, worker: str, reason: str, decisions: list[WorkerDecision]) -> None:
        decisions.append(WorkerDecision(worker=worker, called=False, reason=reason))  # type: ignore[arg-type]
        self.layer.log_call(run_id=self.run_id, agent="crew", step=f"{lead.id}:{worker}", status="skipped", note=reason)

    def _called(self, worker: str, reason: str, decisions: list[WorkerDecision]) -> None:
        decisions.append(WorkerDecision(worker=worker, called=True, reason=reason))  # type: ignore[arg-type]

    # -- one lead ----------------------------------------------------------------------

    async def run_lead(self, lead: Lead) -> TriageResult:
        blocked_before = len(self.blocked)
        decisions: list[WorkerDecision] = []
        reasons: list[str] = []
        calls = []
        enrichment: Enrichment | None = None
        qualification: Qualification | None = None
        outcome: DraftOutcome | None = None

        # 2. duplicate (code, no model): nothing else runs
        dup = find_duplicate(self.hubspot, lead)
        if dup is not None:
            why = f"duplicate of contact {dup.id} (created {dup.created_at})"
            reasons.append(f"Same person as an older contact ({dup.id}); the original carries the triage.")
            for w in ("enricher", "qualifier", "drafter"):
                self._skip(lead, w, why, decisions)
        else:
            # 3. the orchestrator's plan
            p, call = await plan(self, lead)
            calls.append(call)
            if p.summary:
                reasons.append(f"Orchestrator: {p.summary}")

            # 4. enricher
            if lead.properties.has_full_company_profile:
                self._skip(lead, "enricher", "company profile complete on the contact (company, industry, size, website)", decisions)
                enrichment = profile_from_contact(lead)
            elif not p.call_enricher:
                # The model call is skipped; the directory lookup is a fact and still happens in code (no model).
                self._skip(lead, "enricher", f"orchestrator: {p.enricher_reason}", decisions)
                enrichment = enforce_enrichment(self, lead, Enrichment(company_identified=False, note="enricher skipped by the orchestrator"))
            else:
                self._called("enricher", p.enricher_reason, decisions)
                enrichment, call = await enrich(self, lead)
                calls.append(call)

            # 5. qualifier
            if not enrichment.company_identified:
                why = f"company could not be identified ({'; '.join(enrichment.sources)}); nothing to score"
                self._skip(lead, "qualifier", why, decisions)
                self._skip(lead, "drafter", "no qualification", decisions)
                reasons.append("The company is missing or unresolvable; ask the lead which organization they are with.")
            elif not p.call_qualifier:
                self._skip(lead, "qualifier", f"orchestrator: {p.qualifier_reason}", decisions)
                self._skip(lead, "drafter", "no qualification", decisions)
                reasons.append(f"Not qualified — qualifier skipped by the orchestrator: {p.qualifier_reason}")
            else:
                self._called("qualifier", p.qualifier_reason, decisions)
                qualification, call = await qualify(self, lead, enrichment)
                calls.append(call)
                reasons.extend(qualification.profile.reasons)

        band = decide_band(duplicate_of=dup.id if dup else None, enrichment=enrichment, qualification=qualification)

        # 6. drafter: only a consented good fit, decided in code
        if qualification is not None and not any(d.worker == "drafter" for d in decisions):
            if band != "good fit":
                self._skip(lead, "drafter", f"band is {band}; no follow-up", decisions)
            else:
                consent = self.layer.check_consent(email=lead.email, channel="email")
                if not consent.ok or not consent.allowed:
                    why = f"consent: {consent.reason if consent.ok else consent.error.message}"
                    self._skip(lead, "drafter", why, decisions)
                    outcome = DraftOutcome(created=False, reason=why)
                else:
                    self._called("drafter", f"good fit and consented on email (contact {consent.contact_id})", decisions)
                    outcome, call = await draft(self, lead, enrichment, qualification)  # type: ignore[arg-type]
                    calls.append(call)

        result = TriageResult(
            lead_id=lead.id, run_id=self.run_id, band=band, score=qualification.score if qualification else None, reasons=reasons,
            decisions=decisions, duplicate_of=dup.id if dup else None, enrichment=enrichment, qualification=qualification, draft=outcome,
            cost_usd=round(sum(c.cost_usd for c in calls), 6), input_tokens=sum(c.result.billed_input_tokens for c in calls),
            output_tokens=sum(c.result.output_tokens for c in calls), measured=bool(calls) and self.caller.measured,
            blocked_attempts=len(self.blocked) - blocked_before,
        )

        # 7. notes, then measurement (only after the write succeeded)
        if outcome is not None and outcome.created:
            result.draft_note_id = self.hubspot.create_note(lead.id, draft_note(lead, outcome), kind="draft").id
        result.note_id = self.hubspot.create_note(lead.id, triage_note(lead, result), kind="triage").id
        self.layer.record("lead.triaged", {
            "lead_id": lead.id, "band": band, "score": result.score, "workers_called": [d.worker for d in decisions if d.called],
            "workers_skipped": [d.worker for d in decisions if not d.called], "drafted": bool(outcome and outcome.created),
            "cost_usd": result.cost_usd, "measured": result.measured, "blocked_attempts": result.blocked_attempts, "run_id": self.run_id,
        }, run_id=self.run_id)
        self.results.append(result)
        return result

    # -- many leads --------------------------------------------------------------------

    async def run_all(self, leads: list[Lead]) -> list[TriageResult]:
        out = []
        for lead in leads:
            if self.over_cap:
                self.layer.log_call(run_id=self.run_id, agent="crew", step=f"{lead.id}:run", status="skipped", note="over cap: run stopped")
                break
            try:
                out.append(await self.run_lead(lead))
            except OverCap as e:
                self.layer.log_call(run_id=self.run_id, agent="crew", step=f"{lead.id}:run", status="skipped", note=str(e))
                self.over_cap = True
                break
        return out

    def run_cost(self) -> tuple[float, int]:
        t = self.layer.run_total(self.run_id)
        return t.cost_usd, t.calls

    def write_run_log(self, path: Path) -> None:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run_id": self.run_id, "caller": self.caller.name, "measured": self.caller.measured,
                                    "results": [r.model_dump(mode="json") for r in self.results],
                                    "blocked_attempts": [b.as_dict() for b in self.blocked]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
