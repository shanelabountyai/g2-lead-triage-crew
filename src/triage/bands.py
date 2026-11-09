"""Band and duplicate rules (D-13, D-14): one function each, pinned by tests."""

from __future__ import annotations

import re

from triage.hubspot import Contact, HubSpotClient
from triage.models import Band, Enrichment, Lead, Qualification


def decide_band(*, duplicate_of: str | None, enrichment: Enrichment | None, qualification: Qualification | None) -> Band:
    """Precedence: duplicate > student > vendor > missing company info > not qualified > good fit > poor fit.

    `missing company info` only when there is no identified company; a lead whose company *is* identified but whose
    Qualifier was skipped is `not qualified` (D-23)."""
    if duplicate_of:
        return "duplicate"
    rel = qualification.profile.relationship if qualification else None
    if rel == "student":
        return "student"
    if rel == "vendor":
        return "vendor"
    if enrichment is None or not enrichment.company_identified:
        return "missing company info"
    if qualification is None:
        return "not qualified"
    return "good fit" if qualification.passed else "poor fit"


_plus = re.compile(r"\+[^@]*@")


def canonical_email(email: str) -> str:
    """lower-case, +tag stripped: ada.test01+again@example.com -> ada.test01@example.com"""
    return _plus.sub("@", (email or "").strip().lower())


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _age(c: "Contact") -> tuple[str, int, str]:
    """Sort key for "older": createdate, then HubSpot's numeric id. HubSpot ignores a supplied createdate and stamps a whole
    batch with one timestamp (seen live, 2026-11-09), so equal createdates fall back to the id, which only ever grows."""
    return (c.created_at, int(c.id) if c.id.isdigit() else 0, c.id)


def find_duplicate(hubspot: HubSpotClient, lead: Lead) -> Contact | None:
    """The oldest *older* contact that is the same person (D-14), or None."""
    p = lead.properties
    candidates: dict[str, Contact] = {}
    mine = canonical_email(p.email)
    for c in hubspot.find_contacts(email=mine):
        candidates[c.id] = c
    # +tag variants: HubSpot's exact search cannot find them, so ask by name+company too and compare canonically.
    if p.firstname and p.lastname and p.company:
        for c in hubspot.find_contacts(firstname=p.firstname, lastname=p.lastname, company=p.company):
            candidates[c.id] = c
    older = [c for c in candidates.values() if c.id != lead.id and _age(c) < _age(lead) and (
        canonical_email(c.email) == mine
        or (_norm(c.properties.get("firstname")) == _norm(p.firstname) and _norm(c.properties.get("lastname")) == _norm(p.lastname)
            and _norm(c.properties.get("company")) == _norm(p.company) and _norm(p.company) != "")
    )]
    if not older:
        return None
    return sorted(older, key=_age)[0]
