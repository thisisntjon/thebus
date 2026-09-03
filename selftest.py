#!/usr/bin/env python3
"""selftest.py -- offline proof of the governance logic. No network, no gh.

Covers the two rules the protocol exists to encode, in both directions:
  POSITIVE  the violation is caught
  NEGATIVE  the legitimate case is not flagged

ASCII only. Exit 0 = all cases pass.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import bus

PASS, FAIL = [], []
T0 = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)


def case(name, ok, detail=""):
    (PASS if ok else FAIL).append(name if ok else f"{name} :: {detail}")
    print(f"  [{'ok' if ok else '!!'}] {name}" + ("" if ok else f"  <- {detail}"))


def lease(agent, mins, at=T0):
    return {"trailer": {"kind": "lease", "agent": agent,
                        "until": bus.iso(at + timedelta(minutes=mins))}}


def tomb(agent, reason="lease expired"):
    return {"trailer": {"kind": "tombstone", "agent": agent, "reason": reason}}


def dissent(n, agent, measurement, origin=None, title="t"):
    tr = {"kind": "dissent", "agent": agent, "measurement": measurement,
          "kill_criterion": "kc", "prereg": "pr"}
    if origin:
        tr["origin"] = str(origin)
    return {"number": n, "title": title, "trailer": tr}


def main() -> int:
    print("-- wire format --")
    t = bus.parse_trailer("text\n" + bus.emit_trailer(kind="lease", agent="w-1", until="x")
                          + "\nmore")
    case("trailer round-trips", t == {"kind": "lease", "agent": "w-1", "until": "x"}, str(t))
    case("no trailer -> empty dict", bus.parse_trailer("plain text") == {})
    case("trailer is invisible html comment",
         bus.emit_trailer(kind="x").startswith("<!--") and
         bus.emit_trailer(kind="x").rstrip().endswith("-->"))

    print("\n-- rule 1: a name retires by tombstone, not deletion --")
    case("no comments -> vacant", bus.lease_state([], T0)["holder"] is None)
    st = bus.lease_state([lease("worker-3", 45)], T0)
    case("live lease -> held", st["live"] and st["holder"] == "worker-3", str(st))
    st = bus.lease_state([lease("worker-3", 45)], T0 + timedelta(minutes=46))
    case("lease past expiry -> EXPIRED, holder cleared",
         st["expired"] and st["holder"] is None, str(st))
    case("expired seat remembers who to tombstone", st["last_holder"] == "worker-3")
    st = bus.lease_state([lease("worker-3", 45), tomb("worker-3")], T0)
    case("tombstone releases a live lease", st["holder"] is None and not st["live"], str(st))
    st = bus.lease_state([lease("w-3", 45), tomb("w-3"), lease("w-9", 45)], T0)
    case("seat is reusable after a tombstone (name is not)",
         st["live"] and st["holder"] == "w-9", str(st))
    st = bus.lease_state([lease("w-3", 45), lease("w-3", 90)], T0 + timedelta(minutes=60))
    case("heartbeat extends the lease", st["live"] and st["holder"] == "w-3", str(st))
    st = bus.lease_state([lease("w-3", 10), lease("w-9", 60)], T0 + timedelta(minutes=30))
    case("latest lease wins on handover", st["holder"] == "w-9", str(st))

    print("\n-- rule 2: echo must never become consensus --")
    ds = [dissent(1, "a", "eval score fell to 0.41"),
          dissent(2, "b", "cold onboard failed 3/5")]
    case("two members, two measurements -> 2 independent",
         len(bus.independent_dissents(ds)) == 2)
    ds = [dissent(1, "a", "eval score fell to 0.41"),
          dissent(2, "a", "cold onboard failed 3/5")]
    case("one member filing twice -> 1 independent",
         len(bus.independent_dissents(ds)) == 1, "same member is not a second opinion")
    ds = [dissent(1, "a", "eval score fell to 0.41"),
          dissent(2, "b", "Eval  score  fell to 0.41")]
    case("same measurement, different members -> 1 independent",
         len(bus.independent_dissents(ds)) == 1, "same observation is not two observations")
    ds = [dissent(1, "a", "eval fell"), dissent(2, "b", "derived", origin=1)]
    case("derived dissent excluded from quorum",
         len(bus.independent_dissents(ds)) == 1, "an echo cannot vote")
    ds = [dissent(1, "a", "x"), dissent(2, "b", "y"), dissent(3, "c", "z")]
    case("three genuinely independent -> 3", len(bus.independent_dissents(ds)) == 3)

    rows = bus.collapse_echo([dissent(1, "a", "x", title="project is doomed")],
                             {1: [{"trailer": {"agent": f"w-{i}"}} for i in range(5)]})
    case("five restatements render as ONE judgment with 5 citations",
         len(rows) == 1 and rows[0]["citations"] == 5, str(rows))
    case("citing members are named for audit",
         len(rows[0]["citing_agents"]) == 5, str(rows[0]))

    print("\n-- concurrent filing (read-after-write race) --")
    ds = [dissent(6, "a", "2/5 cold onboards passed"),
          dissent(7, "b", "2/5 cold onboards passed")]
    case("racer collapses into the earlier origin",
         bus.find_earlier_duplicate(ds, 7, "2/5 cold onboards passed") == 6)
    case("the earlier origin survives",
         bus.find_earlier_duplicate(ds, 6, "2/5 cold onboards passed") is None)
    ds3 = ds + [dissent(8, "c", "2/5 cold onboards passed")]
    case("three-way race converges on ONE origin",
         {bus.find_earlier_duplicate(ds3, n, "2/5 cold onboards passed")
          for n in (7, 8)} == {6}, "every racer must reach the same verdict alone")
    case("distinct measurement is not collapsed",
         bus.find_earlier_duplicate(ds, 7, "eval score fell to 0.41") is None)
    case("empty measurement never collapses", bus.find_earlier_duplicate(ds, 7, "") is None)

    print("\n-- symmetric evidentiary bar --")
    case("dissent with full triad passes",
         bus.missing_evidence({"kill_criterion": "k", "measurement": "m", "prereg": "p"}) == [])
    case("bare opinion is refused",
         set(bus.missing_evidence({})) == set(bus.EVIDENCE), "no free negatives")
    case("partial evidence names what is missing",
         bus.missing_evidence({"measurement": "m"}) == ["kill_criterion", "prereg"])

    print("\n-- normalization --")
    case("measurement compare ignores case and whitespace",
         bus.norm("  Eval   Score  FELL ") == bus.norm("eval score fell"))

    print(f"\n{'=' * 60}\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAIL: {f}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
