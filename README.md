# thebus

## Status

- **Retired 2026-08-18.** No further work is planned here.
- **Kept as a published negative result.** The design was refuted by a five-angle prior-art
  sweep before anything was built on it. The effort was redirected to a project template
  ("the blueprint") maintained in a sibling repository (publication pending; not linked here).
- **Do not build on it.** `bus.py` implements the retracted design and `AGENTS.md` teaches
  it. Both are kept unedited as the record.
- **What a reader can take from it:** the prior-art sweep in `workflow/research/` (five
  angle reports plus `SYNTHESIS.md`, about 2,700 lines, each claim sourced inline; a
  further ~700-line Phase 1 method note, `phase-1.md`, was added after the sweep) and the
  retraction ledger `RETRACTIONS.md`, which records each withdrawn claim, what killed it,
  and what would have replaced it.
- "Law N" references throughout are to the canon (`LAWS.md`) of that sibling repository
  (publication pending; not linked here). Law 6 is "correct by editing, retract by ledger", which is
  why the retracted files remain in the tree.

The shipped design is separately retracted on its own merits: a five-angle prior-art sweep
invalidated 17 assumptions, including the premise. Do not run `bus.py` as a model of how this
should work. `RETRACTIONS.md` lists what was withdrawn; `workflow/research/SYNTHESIS.md` holds
the evidence. The code stays in the tree as the retracted artifact it is — Law 6, correct by
editing, retract by ledger.

## What this became

An experiment in **cross-harness adversarial review**: one artifact, reviewed by agents
from different model families, aimed at the failure that is actually documented —
**false success**, agents over-claiming completion — rather than the one the original
design assumed.

It is not a fleet, and no longer tries to be. Seats, leases, membership lifecycle and
routing are withdrawn (`RETRACTIONS.md` R6). The owning project's canon already decided
single-agent default, with reopening gated on an ablation that has not run. That ablation
is now Phase 1 here, so the gate gets answered before anything else is built.

## What the sweep established

**The gap is real.** Voting and dissent preservation are absent from MCP, A2A, ACP, ANP
and ERC-8004 — confirmed two independent ways: ANP documents it about itself (its
non-goals exclude consensus mechanisms; its future work names "protocol consensus, voting,
review, and governance mechanisms"), and an OSS survey found zero `quorum` or `dissent`
constructs across the entire surveyed field.

**Riding a standard is closed.** A2A extensions cannot carry this. The mechanism is
`AgentExtension` on the Agent Card plus the `A2A-Extensions` header; the guide's language
about new RPC methods and state machines is non-normative and is contradicted by a
prohibition on adding enum values or changing core structures. Extensions are per-request
against a single agent, and A2A declines to standardize registries.

**The social design was inverted.** No institution quarantines dissent; all of them keep
it readable and strip only its authority. Our specific implementation — dissent shown
under a "disregard this" banner — is the measured-worst option across 48 studies.

**Governance is not the binding constraint.** MAST ranks the failure modes governance
addresses near the bottom of fourteen; specification, verification and stopping conditions
dominate at ~77%.

**What survives, unproven:** model-family heterogeneity as a formal requirement for
quorum. BFT assumes independent failures, and two members on the same base model are not
two samples. No prior art located. Phase 1 tests it, and a known attack
("Gaming Consensus") says diversity requirements invite adversaries who supply diversity.

## How to verify

Run `python selftest.py`; it prints `27 passed, 0 failed`.

## Layout

| path | what |
|---|---|
| `RETRACTIONS.md` | what was withdrawn, why, and what replaces it |
| `workflow/PLAN.md` | living plan — problem, criteria, 32-entry assumption registry (17 entries invalidated by the sweep, 21 after Phase 1 step A), phases |
| `workflow/research/` | five angle reports + `SYNTHESIS.md`, every claim sourced |
| `PROTOCOL.md` | **retracted in parts** — read only alongside `RETRACTIONS.md` |
| `bus.py`, `AGENTS.md` | the retracted prototype, kept as the record |
| `selftest.py` | 27 offline cases; they pass, and they test the retracted design |

## Honest summary

The mechanics were sound and got better under review — GitHub's issue numbers turn out to
be exactly the fencing tokens the leases were missing. The social design was backwards.
The reason to build it at all was closed by a decision nobody had checked.

Phase 1 answers whether there is anything here worth building. A clean negative closes the
question, which is a real result and cheaper than the alternative.
