#!/usr/bin/env python3
"""bus.py -- thebus client.  *** RETRACTED DESIGN -- see RETRACTIONS.md ***

    This code works and its selftest passes, but the design it implements was
    invalidated on 2026-08-18. `orient` prints a dissent banner that a 48-study
    meta-analysis finds measurably backfires; `dissent file` refuses objections from
    anyone unable to fund their own measurement (the Columbia failure); `motion`
    gates on quorum, which makes a correct lone dissenter unactionable. Kept in the
    tree as the record. Do not extend it; Phase 2 rewrites the objection layer.

A governance layer for heterogeneous agent fleets.

Harness-neutral: needs only `gh` (authenticated) and python 3.8+. No MCP, no
skills, no slash commands. Paste-portable into Claude Code, Codex, or anything
else that can run a subprocess.

See PROTOCOL.md. The two rules this encodes:
  1. Route to SEATS, never to member names. Names retire by tombstone, not deletion.
  2. Dissent is preserved, attributed, quarantined, and evidence-gated -- never
     suppressed (suppression is what makes it return as contagion) and never
     broadcast (broadcast is what makes it spread).

ASCII output only. Read-only commands are safe to run at any time.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

TRAILER_RE = re.compile(r"<!--\s*bus\s*(.*?)-->", re.S)
LEASE_MIN = 45          # default lease length; renew with `heartbeat`
DEFAULT_SEATS = ["lead", "worker-1", "worker-2", "verifier", "auditor"]

LABELS = [
    ("bus:seat", "5319e7", "A seat: a leasable role, not a member"),
    ("bus:ticket", "0e8a16", "A unit of work"),
    ("bus:dissent", "b60205", "A registered dissent -- quarantined from ORIENT"),
    ("bus:motion", "d93f0b", "A proposed strategy change -- human gate only"),
    ("bus:audit", "fbca04", "An auditor provenance report"),
    ("seat:held", "0e8a16", "Seat has a live lease"),
    ("seat:vacant", "c5def5", "Seat is open for claim"),
    ("seat:tombstoned", "6a737d", "Seat retired -- do not route work here"),
    ("state:open", "c5def5", "Unclaimed"),
    ("state:claimed", "0e8a16", "Claimed by a seat"),
    ("state:review", "fbca04", "Awaiting independent verification"),
    ("state:done", "0e8a16", "Verified complete"),
    ("state:blocked", "d93f0b", "Blocked"),
    ("gate:human", "e99695", "Only a human may close this"),
    ("quarantine", "6a737d", "Not surfaced during ORIENT"),
]

SEAT_CHARTERS = {
    "lead": "Owns the plan, routing, and merges. Does not build and verify the same object.",
    "worker": "Owns exactly the claimed ticket and its receipts. No self-merge, no strategy.",
    "verifier": "Independently reproduces positive claims. Never verifies its own work.",
    "auditor": "Checks provenance only, never does work. Runs `bus.py audit`.",
}


# ------------------------------------------------------------------ plumbing

def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def emit_trailer(**kw) -> str:
    body = "".join(f"{k}: {v}\n" for k, v in kw.items() if v not in (None, ""))
    return "<!-- bus\n" + body + "-->"


def parse_trailer(text: str) -> dict:
    m = TRAILER_RE.search(text or "")
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def gh(*args, check=True) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write(f"[gh error] {' '.join(args[:3])}: {r.stderr.strip()}\n")
        raise SystemExit(2)
    return r.stdout.strip()


def gh_json(*args):
    out = gh(*args)
    return json.loads(out) if out else []


def repo_of(args) -> str:
    if args.repo:
        return args.repo
    return gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")


def issues(repo: str, label: str, state: str = "open") -> list:
    rows = gh_json("issue", "list", "--repo", repo, "--label", label, "--state", state,
                   "--limit", "200", "--json", "number,title,body,labels,state")
    for r in rows:
        r["labelset"] = {x["name"] for x in r.get("labels", [])}
        r["trailer"] = parse_trailer(r.get("body", ""))
    return sorted(rows, key=lambda r: r["number"])


def comments(repo: str, number: int) -> list:
    rows = gh_json("api", f"repos/{repo}/issues/{number}/comments", "--paginate")
    out = []
    for c in rows:
        t = parse_trailer(c.get("body", ""))
        if t:
            out.append({"trailer": t, "body": c.get("body", ""),
                        "at": c.get("created_at", "")})
    return out


def comment(repo: str, number: int, body: str) -> None:
    gh("issue", "comment", str(number), "--repo", repo, "--body", body)


def relabel(repo: str, number: int, add=(), remove=()) -> None:
    cmd = ["issue", "edit", str(number), "--repo", repo]
    for a in add:
        cmd += ["--add-label", a]
    for r in remove:
        cmd += ["--remove-label", r]
    gh(*cmd)


def create_issue(repo: str, title: str, body: str, labels) -> int:
    cmd = ["issue", "create", "--repo", repo, "--title", title, "--body", body]
    for lbl in labels:
        cmd += ["--label", lbl]
    url = gh(*cmd)
    m = re.search(r"/(\d+)\s*$", url)
    return int(m.group(1)) if m else -1


# ------------------------------------------------------- pure logic (testable)

def lease_state(seat_comments: list, at: datetime) -> dict:
    """Current holder of a seat, from its comment thread. Latest lease/tombstone wins."""
    holder, until, retired = None, None, False
    for c in seat_comments:
        t = c["trailer"]
        if t.get("kind") == "lease":
            holder, until, retired = t.get("agent"), parse_iso(t.get("until", "")), False
        elif t.get("kind") == "tombstone":
            holder, until, retired = None, None, True
    live = bool(holder and until and until > at)
    return {"holder": holder if live else None, "until": until,
            "expired": bool(holder and until and until <= at),
            "last_holder": holder, "retired": retired and not holder, "live": live}


def independent_dissents(dissents: list) -> list:
    """Quorum counts only INDEPENDENT dissent: distinct member, distinct measurement,
    and not itself derived from another dissent. Echo must never become consensus."""
    seen_agents, seen_meas, out = set(), set(), []
    for d in dissents:
        t = d["trailer"]
        if t.get("origin"):
            continue
        agent, meas = t.get("agent", ""), norm(t.get("measurement", ""))
        if not agent or agent in seen_agents or (meas and meas in seen_meas):
            continue
        seen_agents.add(agent)
        if meas:
            seen_meas.add(meas)
        out.append(d)
    return out


def collapse_echo(dissents: list, cites: dict) -> list:
    """Render the register as origins with citation counts, so five restatements of
    one judgment read as one judgment -- not as five findings."""
    rows = []
    for d in dissents:
        cs = cites.get(d["number"], [])
        agents = sorted({c["trailer"].get("agent", "?") for c in cs})
        rows.append({"number": d["number"], "title": d["title"],
                     "agent": d["trailer"].get("agent", "?"),
                     "citations": len(cs), "citing_agents": agents})
    return rows


def find_earlier_duplicate(dissents: list, number: int, measurement: str):
    """Lowest-numbered open dissent registering the same measurement, before `number`.

    GitHub list reads are not immediate after a write, so two members filing the same
    judgment within the same second both clear the pre-check -- which is exactly the
    case the echo guard exists for. Deterministic tie-break (earliest issue wins) lets
    every racer independently reach the same verdict without coordination.
    """
    m = norm(measurement)
    if not m:
        return None
    cands = [d["number"] for d in dissents
             if d["number"] < number and norm(d["trailer"].get("measurement", "")) == m]
    return min(cands) if cands else None


EVIDENCE = ("kill_criterion", "measurement", "prereg")


def missing_evidence(trailer: dict) -> list:
    return [k for k in EVIDENCE if not trailer.get(k)]


# ------------------------------------------------------------------ commands

def cmd_init(args) -> int:
    repo = repo_of(args)
    for name, color, desc in LABELS:
        gh("label", "create", name, "--repo", repo, "--color", color,
           "--description", desc, "--force")
    print(f"[ok] {len(LABELS)} labels")
    existing = {i["title"] for i in issues(repo, "bus:seat", "all")}
    for seat in (args.seats.split(",") if args.seats else DEFAULT_SEATS):
        seat = seat.strip()
        title = f"seat: {seat}"
        if title in existing:
            print(f"[--] {title} exists")
            continue
        charter = SEAT_CHARTERS.get(seat.split("-")[0], "No charter recorded.")
        body = (f"{charter}\n\nThis is a **seat**, not a member. Work is routed here by "
                f"name-of-seat. Whoever holds the lease does the work; when the lease "
                f"expires the seat is reaped and the holder is tombstoned in this thread.\n\n"
                + emit_trailer(kind="seat", seat=seat))
        n = create_issue(repo, title, body, ["bus:seat", "seat:vacant"])
        print(f"[ok] #{n} {title}")
    print("\nNext: bus.py orient")
    return 0


def cmd_seats(args) -> int:
    repo = repo_of(args)
    at = now()
    rows = []
    for s in issues(repo, "bus:seat", "all"):
        seat = s["trailer"].get("seat", s["title"].replace("seat: ", ""))
        st = lease_state(comments(repo, s["number"]), at)
        rows.append({"issue": s["number"], "seat": seat, **st})
    if args.json:
        print(json.dumps([{k: (iso(v) if isinstance(v, datetime) else v)
                           for k, v in r.items()} for r in rows], indent=2))
        return 0
    print("-- roster (route to SEAT, never to member) --")
    print("  {:<5} {:<12} {:<12} {:<14} {}".format("#", "SEAT", "STATE", "HOLDER", "LEASE"))
    for r in rows:
        if r["live"]:
            state, extra = "HELD", f"expires {iso(r['until'])}"
        elif r["expired"]:
            state, extra = "EXPIRED", f"reap: was {r['last_holder']}"
        else:
            state, extra = "VACANT", ""
        print("  {:<5} {:<12} {:<12} {:<14} {}".format(
            r["issue"], r["seat"], state, r["holder"] or "-", extra))
    print("\n  Members are leases. Tombstones live in each seat thread (the ledger).")
    return 0


def cmd_claim_seat(args) -> int:
    repo = repo_of(args)
    at = now()
    for s in issues(repo, "bus:seat", "all"):
        seat = s["trailer"].get("seat", "")
        if seat != args.seat:
            continue
        st = lease_state(comments(repo, s["number"]), at)
        if st["live"] and st["holder"] != args.agent:
            print(f"[!!] seat '{seat}' is held by {st['holder']} until {iso(st['until'])}")
            print("     wait for expiry, or run: bus.py reap")
            return 1
        until = at + timedelta(minutes=args.minutes)
        comment(repo, s["number"], f"Lease claimed by `{args.agent}`.\n\n"
                + emit_trailer(kind="lease", agent=args.agent, seat=seat, until=iso(until)))
        relabel(repo, s["number"], add=["seat:held"],
                remove=["seat:vacant", "seat:tombstoned"])
        print(f"[ok] {args.agent} holds seat '{seat}' (#{s['number']}) until {iso(until)}")
        print(f"     renew before then: bus.py heartbeat --seat {seat} --agent {args.agent}")
        return 0
    print(f"[!!] no such seat: {args.seat}")
    return 1


def cmd_heartbeat(args) -> int:
    repo = repo_of(args)
    for s in issues(repo, "bus:seat", "all"):
        if s["trailer"].get("seat") != args.seat:
            continue
        until = now() + timedelta(minutes=args.minutes)
        comment(repo, s["number"], f"Heartbeat from `{args.agent}`.\n\n"
                + emit_trailer(kind="lease", agent=args.agent, seat=args.seat, until=iso(until)))
        print(f"[ok] lease extended to {iso(until)}")
        return 0
    print(f"[!!] no such seat: {args.seat}")
    return 1


def cmd_release_seat(args) -> int:
    repo = repo_of(args)
    for s in issues(repo, "bus:seat", "all"):
        if s["trailer"].get("seat") != args.seat:
            continue
        comment(repo, s["number"],
                f"**Tombstone.** `{args.agent}` released this seat. Reason: {args.reason}\n\n"
                "Do not route work to this member. The seat is open; the member is history.\n\n"
                + emit_trailer(kind="tombstone", agent=args.agent, seat=args.seat,
                               reason=args.reason))
        relabel(repo, s["number"], add=["seat:vacant"], remove=["seat:held"])
        print(f"[ok] {args.agent} released '{args.seat}' -- tombstoned in #{s['number']}")
        return 0
    print(f"[!!] no such seat: {args.seat}")
    return 1


def cmd_reap(args) -> int:
    repo = repo_of(args)
    at, reaped = now(), 0
    for s in issues(repo, "bus:seat", "all"):
        st = lease_state(comments(repo, s["number"]), at)
        if not st["expired"]:
            continue
        seat = s["trailer"].get("seat", "")
        if args.dry_run:
            print(f"[dry] would reap '{seat}' (held by {st['last_holder']}, "
                  f"expired {iso(st['until'])})")
            reaped += 1
            continue
        comment(repo, s["number"],
                f"**Tombstone.** Lease for `{st['last_holder']}` expired at "
                f"{iso(st['until'])} with no heartbeat.\n\nSeat is vacant. Any work "
                "addressed to this member must be re-routed to the seat.\n\n"
                + emit_trailer(kind="tombstone", agent=st["last_holder"], seat=seat,
                               reason="lease expired"))
        relabel(repo, s["number"], add=["seat:vacant"], remove=["seat:held"])
        print(f"[ok] reaped '{seat}' (was {st['last_holder']})")
        reaped += 1
    print(f"[ok] {reaped} seat(s) reaped" if reaped else "[ok] nothing to reap")
    return 0


def cmd_dissent_file(args) -> int:
    """A strategic claim carries the same receipt a positive result does."""
    repo = repo_of(args)
    missing = [k for k, v in (("kill-criterion", args.kill_criterion),
                              ("measurement", args.measurement),
                              ("prereg", args.prereg)) if not v]
    if missing:
        print("[!!] REFUSED -- dissent needs the same evidence a positive claim needs.")
        print(f"     missing: {', '.join(missing)}")
        print("     'This is failing' is a claim. Claims carry receipts.")
        print("     If you cannot cite a kill criterion that was met, you have a")
        print("     concern, not a finding -- raise it in the ticket thread instead.")
        return 1
    existing = issues(repo, "bus:dissent", "open")
    for d in existing:
        if norm(d["trailer"].get("measurement", "")) == norm(args.measurement):
            print(f"[!!] REFUSED -- #{d['number']} already registers this measurement.")
            print(f"     Do not open a second dissent. Cite the origin:")
            print(f"       bus.py dissent cite {d['number']} --agent {args.agent} --note \"...\"")
            print("     Five restatements of one judgment are one judgment.")
            return 1
    body = (f"**Registered dissent** by `{args.agent}`.\n\n"
            f"## Claim\n{args.claim}\n\n"
            f"## Kill criterion believed met\n{args.kill_criterion}\n\n"
            f"## Measurement\n{args.measurement}\n\n"
            f"## Preregistration cited\n{args.prereg}\n\n"
            "---\nThis is preserved, not suppressed, and quarantined from ORIENT. It is "
            "one member's position, not the fleet's. It becomes a motion only when "
            "independent dissent reaches quorum, and only a human may act on a motion.\n\n"
            + emit_trailer(kind="dissent", agent=args.agent, seat=args.seat or "",
                           kill_criterion=args.kill_criterion[:120],
                           measurement=args.measurement[:120], prereg=args.prereg[:120]))
    n = create_issue(repo, f"dissent: {args.claim[:70]}", body,
                     ["bus:dissent", "quarantine"])
    # Post-write reconcile: the pre-check above reads a lagging index, so a race can
    # still land two origins for one judgment. Collapse to the earliest, deterministically.
    dup = find_earlier_duplicate(issues(repo, "bus:dissent", "open"), n, args.measurement)
    if dup:
        comment(repo, dup, f"Cited by `{args.agent}` (filed concurrently as #{n}, "
                f"collapsed to this origin).\n\n{args.claim}\n\n"
                + emit_trailer(kind="citation", agent=args.agent, origin=str(dup)))
        gh("issue", "close", str(n), "--repo", repo, "--reason", "not planned",
           "--comment", f"Collapsed into #{dup}: same measurement, filed concurrently. "
           "One judgment, not two. The position is preserved as a citation there.")
        print(f"[ok] raced with #{dup} -- collapsed into it as a citation.")
        print("     Your position is preserved. It is still one judgment, not two.")
        return 0
    print(f"[ok] dissent #{n} registered and quarantined.")
    print("     It will not appear in ORIENT. It is not suppressed; it is contained.")
    return 0


def cmd_dissent_cite(args) -> int:
    repo = repo_of(args)
    comment(repo, args.number,
            f"Cited by `{args.agent}`: {args.note}\n\n"
            "(Citation, not a new dissent -- this judgment already has an origin.)\n\n"
            + emit_trailer(kind="citation", agent=args.agent, origin=str(args.number)))
    print(f"[ok] cited #{args.number}. Echo collapsed -- still one judgment.")
    return 0


def cmd_dissent_list(args) -> int:
    repo = repo_of(args)
    ds = issues(repo, "bus:dissent", "open")
    cites = {d["number"]: [c for c in comments(repo, d["number"])
                           if c["trailer"].get("kind") == "citation"] for d in ds}
    rows = collapse_echo(ds, cites)
    indep = independent_dissents(ds)
    if args.json:
        print(json.dumps({"origins": rows, "independent": len(indep)}, indent=2))
        return 0
    print("-- dissent register (quarantined; read only when routed here) --")
    if not rows:
        print("  none registered")
        return 0
    for r in rows:
        print(f"  #{r['number']:<4} {r['title'][:56]}")
        print(f"        origin: {r['agent']}   citations: {r['citations']}"
              + (f" ({', '.join(r['citing_agents'])})" if r['citing_agents'] else ""))
    total_cites = sum(r["citations"] for r in rows)
    print(f"\n  {len(rows)} origin(s), {total_cites} citation(s), "
          f"{len(indep)} INDEPENDENT.")
    print("  Only independent dissent counts toward a motion. Citations are echo.")
    return 0


def cmd_motion(args) -> int:
    repo = repo_of(args)
    ds = issues(repo, "bus:dissent", "open")
    indep = independent_dissents(ds)
    if len(indep) < args.quorum:
        print(f"[!!] REFUSED -- motion needs {args.quorum} INDEPENDENT dissents, "
              f"found {len(indep)}.")
        print("     Independent means: different member, different measurement, not")
        print("     derived from another dissent. Citations do not count.")
        print("     One member's conclusion is not the fleet's strategy.")
        return 1
    refs = ", ".join(f"#{d['number']}" for d in indep)
    body = (f"**Motion** filed by `{args.agent}`.\n\n## Proposed change\n{args.change}\n\n"
            f"## Independent dissent reaching quorum\n{refs}\n\n"
            "---\n**A human closes this. No agent may act on it.** Until it is closed by a "
            "human, the current plan stands and the fleet keeps working it. Do not "
            "pre-emptively wind down, re-scope, or slow work on the strength of a filed "
            "motion.\n\n"
            + emit_trailer(kind="motion", agent=args.agent, quorum=str(len(indep))))
    n = create_issue(repo, f"motion: {args.change[:70]}", body,
                     ["bus:motion", "gate:human"])
    print(f"[ok] motion #{n} filed with quorum {len(indep)} ({refs}).")
    print("     Gated to a human. The plan stands until a human says otherwise.")
    return 0


def cmd_orient(args) -> int:
    """Scoreboard FIRST. The corpus is selected for problems; the order is the fix."""
    repo = repo_of(args)
    done = issues(repo, "state:done", "all")
    tickets_open = [t for t in issues(repo, "bus:ticket", "open")
                    if "state:done" not in t["labelset"]]
    gates = issues(repo, "gate:human", "open")
    dissents = issues(repo, "bus:dissent", "open")
    seats = issues(repo, "bus:seat", "all")
    at = now()
    held = sum(1 for s in seats if lease_state(comments(repo, s["number"]), at)["live"])

    if args.json:
        print(json.dumps({"done": len(done), "open": len(tickets_open),
                          "gates": len(gates), "dissents": len(dissents),
                          "seats_held": held, "seats_total": len(seats)}, indent=2))
        return 0

    print("!" * 62)
    print("RETRACTED DESIGN -- the dissent handling below is invalidated.")
    print("See RETRACTIONS.md R1: hiding dissent under a 'disregard' banner is the")
    print("measured-worst option. This output is preserved as a record, not a model.")
    print("!" * 62)
    print("=" * 62)
    print("SCOREBOARD")
    print("=" * 62)
    print(f"  verified done   : {len(done)}")
    print(f"  seats held      : {held}/{len(seats)}")
    for d in done[-5:]:
        print(f"    [done] #{d['number']} {d['title'][:52]}")
    if not done:
        print("    (nothing banked yet -- this is a new board, not a failing one)")
    print()
    print("-" * 62)
    print("ACTIVE WORK")
    print("-" * 62)
    for t in tickets_open[:12]:
        state = next((l for l in t["labelset"] if l.startswith("state:")), "state:open")
        print(f"  #{t['number']:<4} [{state[6:]:<8}] {t['title'][:44]}")
    if not tickets_open:
        print("  none open -- claim a seat and open a ticket")
    if gates:
        print()
        print("-" * 62)
        print(f"WAITING ON A HUMAN ({len(gates)})")
        print("-" * 62)
        for g in gates:
            print(f"  #{g['number']} {g['title'][:52]}")
    print()
    print("-" * 62)
    if dissents:
        print(f"DISSENT REGISTER: {len(dissents)} open. NOT SHOWN.")
        print("  Preserved and attributed, but quarantined from orientation. It is one")
        print("  member's position, not the fleet's. Do not let it set your priors.")
        print("  Read it only if routed there: bus.py dissent list")
    else:
        print("DISSENT REGISTER: empty.")
    print("-" * 62)
    return 0


def cmd_audit(args) -> int:
    repo = repo_of(args)
    at, findings = now(), []
    for s in issues(repo, "bus:seat", "all"):
        st = lease_state(comments(repo, s["number"]), at)
        seat = s["trailer"].get("seat", "?")
        if st["expired"]:
            findings.append(f"seat '{seat}' (#{s['number']}) lease expired for "
                            f"{st['last_holder']} -- run reap, work may be routed to a ghost")
        if st["live"] and "seat:held" not in s["labelset"]:
            findings.append(f"seat '{seat}' has a live lease but is not labelled seat:held")
    for d in issues(repo, "bus:dissent", "open"):
        miss = missing_evidence(d["trailer"])
        if miss:
            findings.append(f"dissent #{d['number']} lacks evidence: {', '.join(miss)}")
        if "quarantine" not in d["labelset"]:
            findings.append(f"dissent #{d['number']} is NOT quarantined -- it will leak "
                            "into ORIENT and set priors for every fresh member")
    seen = {}
    for d in issues(repo, "bus:dissent", "open"):
        m = norm(d["trailer"].get("measurement", ""))
        if m and m in seen:
            findings.append(f"dissent #{d['number']} duplicates #{seen[m]} -- should be a "
                            "citation; echo is being counted as evidence")
        elif m:
            seen[m] = d["number"]
    for m in issues(repo, "bus:motion", "open"):
        if "gate:human" not in m["labelset"]:
            findings.append(f"motion #{m['number']} is not human-gated -- an agent could act on it")
    if args.json:
        print(json.dumps({"findings": findings, "clean": not findings}, indent=2))
        return 1 if findings else 0
    print("-- provenance audit --")
    for f in findings:
        print(f"  [!!] {f}")
    print(f"  [ok] clean" if not findings else f"\n  {len(findings)} finding(s)")
    if args.post and findings:
        body = "Auditor report.\n\n" + "\n".join(f"- {f}" for f in findings) + "\n\n" \
               + emit_trailer(kind="verdict", agent=args.agent or "auditor")
        n = create_issue(repo, f"audit: {len(findings)} provenance finding(s)", body,
                         ["bus:audit"])
        print(f"  posted as #{n}")
    return 1 if findings else 0


def cmd_ticket(args) -> int:
    repo = repo_of(args)
    if args.action == "open":
        body = (f"## Acceptance criteria\n{args.criteria}\n\n"
                "Locked before the builder starts; the builder does not edit them.\n\n"
                + emit_trailer(kind="ticket", seat=args.seat or ""))
        n = create_issue(repo, args.title, body, ["bus:ticket", "state:open"])
        print(f"[ok] ticket #{n}")
    elif args.action == "claim":
        comment(repo, args.number, f"Claimed by seat `{args.seat}` (member `{args.agent}`).\n\n"
                + emit_trailer(kind="claim", agent=args.agent, seat=args.seat))
        relabel(repo, args.number, add=["state:claimed"], remove=["state:open"])
        print(f"[ok] #{args.number} claimed by seat '{args.seat}'")
    elif args.action == "done":
        comment(repo, args.number, f"Verified by `{args.agent}`.\n\n{args.note}\n\n"
                + emit_trailer(kind="verdict", agent=args.agent, seat=args.seat or ""))
        relabel(repo, args.number, add=["state:done"],
                remove=["state:claimed", "state:review", "state:open"])
        print(f"[ok] #{args.number} done")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="bus.py", description="thebus fleet governance client")
    p.add_argument("--repo", default=None, help="owner/name (default: current repo)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create labels and seats")
    s.add_argument("--seats", default=None, help="comma list (default: %s)" % ",".join(DEFAULT_SEATS))
    s = sub.add_parser("orient", help="scoreboard first, dissent quarantined")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("seats", help="roster: seats, holders, leases")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("claim-seat")
    s.add_argument("seat"); s.add_argument("--agent", required=True)
    s.add_argument("--minutes", type=int, default=LEASE_MIN)
    s = sub.add_parser("heartbeat")
    s.add_argument("--seat", required=True); s.add_argument("--agent", required=True)
    s.add_argument("--minutes", type=int, default=LEASE_MIN)
    s = sub.add_parser("release-seat")
    s.add_argument("--seat", required=True); s.add_argument("--agent", required=True)
    s.add_argument("--reason", default="work complete")
    s = sub.add_parser("reap", help="tombstone expired leases")
    s.add_argument("--dry-run", action="store_true")

    d = sub.add_parser("dissent").add_subparsers(dest="sub", required=True)
    f = d.add_parser("file")
    f.add_argument("--agent", required=True); f.add_argument("--seat", default="")
    f.add_argument("--claim", required=True)
    f.add_argument("--kill-criterion", default=""); f.add_argument("--measurement", default="")
    f.add_argument("--prereg", default="")
    c = d.add_parser("cite")
    c.add_argument("number", type=int); c.add_argument("--agent", required=True)
    c.add_argument("--note", default="concur")
    l = d.add_parser("list"); l.add_argument("--json", action="store_true")

    s = sub.add_parser("motion", help="propose a strategy change (human gate)")
    s.add_argument("--agent", required=True); s.add_argument("--change", required=True)
    s.add_argument("--quorum", type=int, default=2)
    s = sub.add_parser("audit", help="provenance check")
    s.add_argument("--json", action="store_true"); s.add_argument("--post", action="store_true")
    s.add_argument("--agent", default="auditor")

    s = sub.add_parser("ticket")
    s.add_argument("action", choices=["open", "claim", "done"])
    s.add_argument("--number", type=int); s.add_argument("--title", default="")
    s.add_argument("--criteria", default=""); s.add_argument("--seat", default="")
    s.add_argument("--agent", default=""); s.add_argument("--note", default="")

    args = p.parse_args()
    if args.cmd == "dissent":
        return {"file": cmd_dissent_file, "cite": cmd_dissent_cite,
                "list": cmd_dissent_list}[args.sub](args)
    return globals()["cmd_" + args.cmd.replace("-", "_")](args)


if __name__ == "__main__":
    sys.exit(main())
