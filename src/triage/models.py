"""Typed hand-offs between the crew's parts (D-11). Pydantic models, nothing else."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Band = Literal["good fit", "poor fit", "student", "vendor", "duplicate", "missing company info"]
BANDS: tuple[Band, ...] = ("good fit", "poor fit", "student", "vendor", "duplicate", "missing company info")

Role = Literal["executive-sponsor", "pilot-lead", "team-member", "outside-advisor"]
Relationship = Literal["buyer", "vendor", "student", "advisor"]
SizeBand = Literal["1-10", "11-50", "51-200", "201-1000", "1001-5000", "5000+"]
STALLED_STAGES = ("running-no-decision", "finished-not-rolled-out", "rolled-out-low-use")

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
REPO_DIR = FIXTURES_DIR.parent


# -- the lead as HubSpot holds it ---------------------------------------------


class LeadProperties(BaseModel):
    """The contact properties the crew reads. Names are HubSpot's (li_tool_* from li-lead-gen-tools D-13)."""

    model_config = ConfigDict(extra="allow")

    email: str
    firstname: str | None = None
    lastname: str | None = None
    company: str | None = None
    jobtitle: str | None = None
    industry: str | None = None
    numberofemployees: int | None = None
    website: str | None = None
    li_tool_name: str | None = None
    li_tool_role: str | None = None
    li_tool_pilot_stage: str | None = None
    li_tool_result: str | None = None
    li_tool_people_gap: int | None = None
    li_tool_process_gap: int | None = None
    li_tool_technology_gap: int | None = None
    li_tool_lead_grade: str | None = None
    message: str | None = None

    @property
    def max_gap(self) -> int:
        return max(self.li_tool_people_gap or 0, self.li_tool_process_gap or 0, self.li_tool_technology_gap or 0)

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.firstname, self.lastname) if p).strip()

    @property
    def has_full_company_profile(self) -> bool:
        """D-19: company, industry, size and website all present on the contact."""
        return all([(self.company or "").strip(), (self.industry or "").strip(), self.numberofemployees, (self.website or "").strip()])


class Lead(BaseModel):
    id: str
    created_at: str
    properties: LeadProperties

    @property
    def email(self) -> str:
        return self.properties.email


class Label(BaseModel):
    band: Band
    why: str = ""


class LabeledLead(Lead):
    label: Label


# -- the synthetic company directory (D-6) ----------------------------------------


class Company(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    domain: str
    industry: str
    size_band: SizeBand
    employees: int
    hq: str
    kind: Literal["company", "education", "vendor", "agency"]
    summary: str


# -- worker outputs ------------------------------------------------------------------


class OrchestratorPlan(BaseModel):
    """What the Orchestrator agent decided (D-12). The crew applies the hard rules on top."""

    call_enricher: bool
    enricher_reason: str
    call_qualifier: bool
    qualifier_reason: str
    summary: str = ""


class Enrichment(BaseModel):
    """The Enricher's structured answer: company fields plus where each came from."""

    company_identified: bool
    company: str | None = None
    industry: str | None = None
    size_band: SizeBand | None = None
    employees: int | None = None
    kind: Literal["company", "education", "vendor", "agency", "unknown"] = "unknown"
    role_title: str | None = None
    sources: list[str] = Field(default_factory=list, description="Where each field came from: the directory record, the contact itself.")
    note: str = ""


class LeadProfile(BaseModel):
    """The Qualifier's structured answer: the normalized fields the rubric scores, plus its reasons.
    The score itself is not here: G0 `evaluation` produces it (D-2, D-13)."""

    role: Role | None = Field(default=None, description="Decision role as the buyer definition names it; inferred from the title when the form left it blank.")
    relationship: Relationship
    pilot_stage: str | None = None
    company: str | None = None
    size_band: SizeBand | None = None
    gap_at_least_6: bool = False
    reasons: list[str] = Field(default_factory=list)


class Draft(BaseModel):
    subject: str
    body: str
    rationale: str = ""


# -- the crew's result per lead ----------------------------------------------------


class WorkerDecision(BaseModel):
    worker: Literal["enricher", "qualifier", "drafter"]
    called: bool
    reason: str


class CriterionNote(BaseModel):
    criterion: str
    score: float
    weight: float
    required: bool
    note: str


class Qualification(BaseModel):
    score: int = Field(ge=0, le=100)
    passed: bool
    judge: str
    evaluation_id: str
    criteria: list[CriterionNote]
    profile: LeadProfile


class DraftOutcome(BaseModel):
    created: bool
    reason: str
    draft: Draft | None = None
    brand_passed: bool | None = None
    brand_violations: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list, description="One line per claim the registry could not support.")


class TriageResult(BaseModel):
    lead_id: str
    run_id: str
    band: Band
    score: int | None = None
    reasons: list[str] = Field(default_factory=list)
    decisions: list[WorkerDecision] = Field(default_factory=list)
    duplicate_of: str | None = None
    enrichment: Enrichment | None = None
    qualification: Qualification | None = None
    draft: DraftOutcome | None = None
    note_id: str | None = None
    draft_note_id: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    measured: bool = False
    blocked_attempts: int = 0


# -- loaders ---------------------------------------------------------------------------


def load_leads(path: Path | None = None) -> list[LabeledLead]:
    doc = json.loads((path or FIXTURES_DIR / "leads.json").read_text(encoding="utf-8"))
    return [LabeledLead.model_validate(x) for x in doc["leads"]]


def load_companies(path: Path | None = None) -> list[Company]:
    doc = json.loads((path or FIXTURES_DIR / "companies.json").read_text(encoding="utf-8"))
    return [Company.model_validate(x) for x in doc["companies"]]


def dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
