"""The shared layer (G0·C), called in-process (D-2, D-12 of G1·C).

One adapter so every capability call in the crew goes through one place and is counted. Every method returns the
capability's typed `Output`; a `Refusal` becomes `Output(ok=False, error=…)` exactly as G0's MCP server does, so
`ok: false` is a result the caller reads, never an exception (g0 docs/attach.md, "Rules for every consumer").

The one addition over G1·C's adapter: `load_rubric` seeds this repo's Qualifier rubric (`rubrics/lead_fit_v1.json`)
into the layer's rubric store through G0's own seed loader, because the evaluation contract has no register tool
(D-2). It is idempotent and namespaced (`g2_lead_fit_v1`); G0's own three rubrics are untouched.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from shared_layer.capabilities import audience_consent, brand_policy, claims_registry, evaluation, health, measurement, observability
from shared_layer.contracts import contract_versions
from shared_layer.errors import Refusal, ToolError
from shared_layer.storage import Database, open_database

from triage.models import REPO_DIR

RUBRIC_FILE = REPO_DIR / "rubrics" / "lead_fit_v1.json"
RUBRIC_ID = "g2_lead_fit_v1"


class LayerDegraded(RuntimeError):
    """health reported `degraded`, or our rubric is missing; the run must not start (attach.md step 3)."""


class Layer:
    def __init__(self, db_path: str | None = None, db: Database | None = None, rubric_file: Path | None = None) -> None:
        self.db = db or open_database(db_path)
        self.calls: Counter[str] = Counter()
        self.rubric_file = rubric_file or RUBRIC_FILE
        self.load_rubric()

    def close(self) -> None:
        self.db.close()

    # -- the one way a call is made ------------------------------------------

    def _run(self, module: Any, **kwargs: Any) -> Any:
        self.calls[module.TOOL] += 1
        Output = module.Output
        try:
            inp = module.Input(**kwargs)
        except ValidationError as e:
            return Output(ok=False, error=ToolError(code="INVALID_ARGUMENT", message=str(e).splitlines()[0]))
        try:
            return module.run(self.db, inp)
        except Refusal as r:
            return Output(ok=False, error=r.envelope)
        except sqlite3.Error as e:
            return Output(ok=False, error=ToolError(code="STORAGE_ERROR", message=f"SQLite refused the operation: {e}"))

    # -- the rubric (D-2) ---------------------------------------------------------

    def load_rubric(self) -> str:
        doc = json.loads(self.rubric_file.read_text(encoding="utf-8"))
        ids = [r["id"] for r in doc["rubrics"]]
        if any(not i.startswith("g2_") for i in ids):
            raise LayerDegraded(f"this consumer may only seed rubrics namespaced g2_*, got {ids}")
        with self.db.conn:
            self.db._seed_rubrics(doc)  # G0's own idempotent loader (INSERT OR REPLACE by id)
        return ids[0]

    # -- capabilities ------------------------------------------------------------

    def health(self) -> health.Output:
        self.calls[health.TOOL] += 1
        return health.run(self.db, health.Input(), contracts=contract_versions())

    def require_healthy(self) -> health.Output:
        h = self.health()
        if h.status != "ok":
            raise LayerDegraded(f"shared layer degraded: writable={h.db_writable} seeds={h.seeds} at {h.db_path}")
        if RUBRIC_ID not in h.rubrics:
            raise LayerDegraded(f"rubric {RUBRIC_ID} is not in the layer's store (have {h.rubrics})")
        return h

    def check_consent(self, *, email: str | None = None, contact_id: str | None = None, channel: str = "email") -> audience_consent.Output:
        return self._run(audience_consent, email=email, contact_id=contact_id, channel=channel)

    def check_brand(self, text: str, channel: str = "email") -> brand_policy.Output:
        return self._run(brand_policy, text=text, channel=channel)

    def check_claims(self, text: str | None = None, claims: list[str] | None = None) -> claims_registry.Output:
        return self._run(claims_registry, text=text, claims=claims)

    def evaluate(self, item: str | dict[str, Any], *, rubric_id: str = RUBRIC_ID, context: str | None = None,
                 run_id: str | None = None, judge: str = "deterministic") -> evaluation.Output:
        return self._run(evaluation, rubric_id=rubric_id, item=item, context=context, judge=judge, run_id=run_id)

    def log_call(self, *, run_id: str, agent: str, step: str, model: str | None = None, input_tokens: int = 0, output_tokens: int = 0,
                 cost_usd: float = 0.0, status: str = "ok", duration_ms: int | None = None, note: str | None = None) -> observability.Output:
        return self._run(observability, run_id=run_id, agent=agent, step=step, model=model, input_tokens=input_tokens,
                         output_tokens=output_tokens, cost_usd=cost_usd, status=status, duration_ms=duration_ms, note=note)

    def run_total(self, run_id: str) -> observability.RunTotal:
        return observability.run_total(self.db, run_id)

    def record(self, event: str, fields: dict[str, Any], run_id: str, agent: str = "crew") -> measurement.Output:
        return self._run(measurement, event=event, fields=fields, run_id=run_id, agent=agent)

    # -- cost helpers (G0's price table; this repo has none of its own, D-10) ------

    @staticmethod
    def prices_per_mtok() -> dict[str, tuple[float, float]]:
        return dict(evaluation.PRICES_PER_MTOK)

    @classmethod
    def cost_usd(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        p_in, p_out = cls.prices_per_mtok().get(model, (0.0, 0.0))
        return round(input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6, 6)

    @staticmethod
    def cap_usd() -> float:
        return observability.cap_usd()
