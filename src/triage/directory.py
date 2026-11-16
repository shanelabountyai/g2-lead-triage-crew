"""The synthetic company directory (D-6): the Enricher's whole world. No web lookup in this build."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from triage.models import Company, load_companies

# Values a lead types that name no organization.
PLACEHOLDERS = {"", "self", "n/a", "na", "none", "-", "me", "myself", "personal", "private", "freelance", "freelancer", "individual", "tbd", "unknown"}


def normalize(name: str | None) -> str:
    n = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    n = re.sub(r"\b(inc|incorporated|llc|ltd|limited|plc|corp|corporation|co|company|llp|the)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


class Directory:
    def __init__(self, companies: list[Company] | None = None, path: Path | None = None) -> None:
        self.companies = companies if companies is not None else load_companies(path)
        self._index: dict[str, Company] = {}
        for c in self.companies:
            for alias in [c.name, *c.aliases]:
                self._index[normalize(alias)] = c

    def is_placeholder(self, name: str | None) -> bool:
        return (name or "").strip().lower() in PLACEHOLDERS

    def lookup(self, name: str | None) -> tuple[Company | None, str]:
        """Return (record, how). `how` is one of exact, alias, fuzzy, placeholder, not_found."""
        if self.is_placeholder(name):
            return None, "placeholder"
        key = normalize(name)
        if not key:
            return None, "placeholder"
        hit = self._index.get(key)
        if hit is not None:
            return hit, "exact" if key == normalize(hit.name) else "alias"
        close = difflib.get_close_matches(key, list(self._index), n=1, cutoff=0.88)
        if close:
            return self._index[close[0]], "fuzzy"
        return None, "not_found"
