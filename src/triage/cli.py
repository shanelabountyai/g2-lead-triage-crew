"""`triage` — run the crew on the fixtures, serve the webhook, replay the fixtures into it, print the HubSpot load payload."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from triage.crew import Crew
from triage.evalreport import accuracy, build_report
from triage.hubspot import FakeHubSpot, HubSpotClient, client_from_env
from triage.layer import Layer
from triage.llm import caller_from_env
from triage.models import FIXTURES_DIR, REPO_DIR, load_leads


def _hubspot_for_serve() -> HubSpotClient:
    """The real client when HUBSPOT_PRIVATE_APP_TOKEN is set (its note writes stay behind `assert_synthetic`, D-7);
    otherwise the fake, seeded from the fixture leads so a replayed objectId resolves (D-20)."""
    if os.environ.get("HUBSPOT_PRIVATE_APP_TOKEN"):
        return client_from_env()
    return FakeHubSpot.seeded(list(load_leads()))


def _crew(args: argparse.Namespace, hubspot: HubSpotClient | None = None) -> Crew:
    cap = float(os.environ.get("G0_RUN_CAP_USD", "10"))
    caller = caller_from_env(record=getattr(args, "record", False), cap_usd=cap)
    if caller.name == "recorded":
        print("no ANTHROPIC_API_KEY: running on fixtures with the recorded-response fake (D-16); cost is not measured live", file=sys.stderr)
    else:
        print(f"ANTHROPIC_API_KEY present: live model calls through the Claude Agent SDK, cap ${cap:.2f} (D-10)", file=sys.stderr)
    judge = getattr(args, "judge", "deterministic")
    if hubspot is not None:
        return Crew(layer=Layer(os.environ.get("G0_DB_PATH")), hubspot=hubspot, caller=caller, judge=judge)
    return Crew.for_fixtures(caller=caller, layer=Layer(os.environ.get("G0_DB_PATH")), judge=judge)


def cmd_run(args: argparse.Namespace) -> int:
    leads = load_leads()
    crew = _crew(args)
    results = asyncio.run(crew.run_all(leads))
    out = Path(args.out) / crew.run_id
    out.mkdir(parents=True, exist_ok=True)
    crew.write_run_log(out / "run-log.json")
    (out / "notes.md").write_text("\n\n---\n\n".join(f"### {n.contact_id} · {n.kind} · {n.id}\n\n```\n{n.body}\n```" for n in crew.hubspot.notes) + "\n", encoding="utf-8")
    report = build_report(crew, leads, results)
    (out / "eval-report.md").write_text(report, encoding="utf-8")
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    correct, total, _ = accuracy(leads, results)
    cost, calls = crew.run_cost()
    measured = bool(results) and all(r.measured for r in results)
    print(f"run {crew.run_id}: {len(results)} leads, {len(crew.hubspot.notes)} notes, band accuracy {correct}/{total}, "
          f"cost {'$%.4f' % cost if measured else 'not measured live'}, blocked attempts {len(crew.blocked)}, layer calls {calls}")
    print(f"wrote {out}/run-log.json, notes.md, eval-report.md" + (f" and {args.report}" if args.report else ""))
    return 0 if len(results) == len(leads) else 1


def cmd_eval(args: argparse.Namespace) -> int:
    doc = json.loads(Path(args.run_log).read_text(encoding="utf-8"))
    leads = load_leads()
    by = {r["lead_id"]: r for r in doc["results"]}
    correct = sum(1 for lead in leads if by.get(lead.id, {}).get("band") == lead.label.band)
    print(f"run {doc['run_id']} ({doc['caller']}, measured={doc['measured']}): band accuracy {correct}/{len(leads)}")
    for lead in leads:
        r = by.get(lead.id)
        got = r["band"] if r else "not processed"
        print(f"  {'OK' if got == lead.label.band else 'XX'} {lead.id} label={lead.label.band!r} got={got!r} score={r.get('score') if r else None}")
    return 0


def hubspot_label(hubspot: HubSpotClient) -> str:
    return "real (writes: notes on synthetic @example.com contacts only, D-7)" if hubspot.name == "real" else "fake (seeded from fixtures)"


def serve_app(args: argparse.Namespace) -> tuple[Any, str]:
    """Build the webhook app and the banner from what was actually built (D-20)."""
    from triage.webhook import create_app

    hubspot = _hubspot_for_serve()  # built here so the banner reports it; the crew (SQLite) is built in the server's loop
    live = hubspot.name == "real" or bool(os.environ.get("ANTHROPIC_API_KEY"))
    # raises UnsignedLiveConfig when live and no HUBSPOT_CLIENT_SECRET (D-21)
    app = create_app(lambda: _crew(args, hubspot=hubspot), public_url=args.public_url, live=live)
    signature = "on" if os.environ.get("HUBSPOT_CLIENT_SECRET") else "off — fixture/fake mode only (fake HubSpot, recorded model, no HUBSPOT_CLIENT_SECRET)"
    banner = (f"serving on http://{args.host}:{args.port} — POST /hubspot/webhook, GET /health; HubSpot client: {hubspot_label(hubspot)}; "
              f"model: {'live' if os.environ.get('ANTHROPIC_API_KEY') else 'recorded fake'}; signature check: {signature}")
    return app, banner


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from triage.webhook import UnsignedLiveConfig

    try:
        app, banner = serve_app(args)
    except UnsignedLiveConfig as e:
        print(f"triage serve: {e}", file=sys.stderr)
        return 2
    print(banner, file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Post one contact.creation event per fixture lead to a running `triage serve`."""
    import httpx

    from triage.webhook import event_for

    leads = load_leads()
    ids = args.ids or [lead.id for lead in leads]
    url = args.url.rstrip("/") + "/hubspot/webhook"
    with httpx.Client(timeout=args.timeout) as client:
        for i in range(0, len(ids), args.batch):
            batch = [event_for(cid) for cid in ids[i:i + args.batch]]
            r = client.post(url, json=batch)
            print(f"POST {url} [{len(batch)} events] -> {r.status_code}")
            try:
                for p in r.json().get("processed", []):
                    print("  ", json.dumps(p))
            except ValueError:
                print("  ", r.text[:300])
    return 0


def cmd_hubspot_load(args: argparse.Namespace) -> int:
    """Print the batch-create payload for the 20 synthetic leads. The live write is the owner's hand step (D-8)."""
    leads = load_leads()
    inputs = []
    for lead in leads:
        props = {k: v for k, v in lead.properties.model_dump().items() if v not in (None, "")}
        props.pop("message", None)  # not a standard property; the owner creates `message` or drops it
        inputs.append({"properties": {k: str(v) for k, v in props.items()}})
    payload = {"inputs": inputs}
    path = Path(args.out)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(inputs)} contacts for POST https://api.hubapi.com/crm/v3/objects/contacts/batch/create")
    print("This command never calls HubSpot. When you are ready (NEXT.md H3), from your own machine:")
    print(f'  curl -sS -X POST https://api.hubapi.com/crm/v3/objects/contacts/batch/create -H "Authorization: Bearer $HUBSPOT_PRIVATE_APP_TOKEN" -H "Content-Type: application/json" --data @{path}')
    print("Every email is on example.com; the li_tool_* properties must exist in the portal (they do: li-lead-gen-tools D-24).")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="triage", description="Lead Triage Crew (G2·C)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run the crew on fixtures/leads.json (recorded fake without a key; live with one)")
    p.add_argument("--fixtures", action="store_true", default=True, help="(always on) the 20 synthetic leads")
    p.add_argument("--record", action="store_true", help="with a key: overwrite fixtures/recorded-responses.json with the live responses")
    p.add_argument("--judge", choices=["deterministic", "claude"], default="deterministic", help="G0 evaluation judge for the rubric")
    p.add_argument("--out", default=str(REPO_DIR / "out"), help="where run-log.json, notes.md and eval-report.md go")
    p.add_argument("--report", default=None, help="also write the eval report here (e.g. docs/eval-report.md)")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("eval", help="band accuracy from a saved run log")
    p.add_argument("--run-log", required=True)
    p.set_defaults(fn=cmd_eval)

    p = sub.add_parser("serve", help="serve the HubSpot webhook")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8042)
    p.add_argument("--judge", choices=["deterministic", "claude"], default="deterministic")
    p.add_argument("--public-url", default=None, help="the URL HubSpot signs against when behind a tunnel (for the v3 signature)")
    p.set_defaults(fn=cmd_serve)

    p = sub.add_parser("replay", help="post the fixture leads as contact.creation events to a running server")
    p.add_argument("--url", default="http://127.0.0.1:8042")
    p.add_argument("--batch", type=int, default=5)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("ids", nargs="*", help="lead ids (default: all 20)")
    p.set_defaults(fn=cmd_replay)

    p = sub.add_parser("hubspot-load", help="print the batch-create payload for the synthetic leads (never calls HubSpot)")
    p.add_argument("--out", default=str(FIXTURES_DIR / "hubspot-batch-create.json"))
    p.set_defaults(fn=cmd_hubspot_load)

    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
