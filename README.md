# thebus

NEGATIVE RESULT · RETIRED 2026-08-18

A preserved negative result: a multi-agent bus design refuted by a five-angle prior-art sweep before anything was built on it.

**Research question:** What happens when the original architecture fails prior-art review?

**What the sweep established**

- The social design was inverted: no institution quarantines dissent, and showing it under a "disregard this" banner is the measured-worst option across 48 studies.
- 17 assumptions invalidated in the initial sweep; 21 after a later step.

Retraction ledger: [`RETRACTIONS.md`](RETRACTIONS.md).

**Do not build on this design.** `bus.py` and `AGENTS.md` are kept unedited as the record.

**Verify:** `python selftest.py` prints `27 passed, 0 failed`.

**Limitations:** the tests exercise the retracted design. The sibling repository ("the blueprint"; the canon behind every "Law N" reference) is [seed-protocol](https://github.com/thisisntjon/seed-protocol). Law 6, "correct by editing, retract by ledger", is why the retracted files remain in the tree.

**Deeper documentation:** [`workflow/PLAN.md`](workflow/PLAN.md) · [`workflow/research/SYNTHESIS.md`](workflow/research/SYNTHESIS.md) · [`workflow/research/`](workflow/research/) · [`PROTOCOL.md`](PROTOCOL.md) (retracted in parts)

## What this became

An experiment in **cross-harness adversarial review**: one artifact, reviewed by agents
from different model families, aimed at the documented failure (**false success**, agents
over-claiming completion) rather than the one the original design assumed.

It is not a fleet. Seats, leases, membership lifecycle and routing are withdrawn
(`RETRACTIONS.md` R6). The owning project's canon had already decided single-agent
default, with reopening gated on an ablation (Phase 1 here) that never ran.

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

**What survives, untested:** model-family heterogeneity as a formal requirement for
quorum. BFT assumes independent failures, and two members on the same base model are not
two samples. No prior art located. Phase 1 was to test it; a known attack ("Gaming
Consensus") says diversity requirements invite adversaries who supply diversity.

## Honest summary

The mechanics were sound and got better under review: GitHub's issue numbers turn out to
be exactly the fencing tokens the leases were missing. The social design was backwards.
The reason to build it at all was closed by a decision nobody had checked. Phase 1 would
have settled whether anything here was worth building; it never ran.

## Part of the Simone Systems Research program

SEED measures whether agent-driven work constitutes verified progress. BigBoss controls which autonomous actions can occur and preserves human decision authority. The Council tests independent verification through heterogeneous model families. The Bus shows adversarial review terminating a bad architecture before further implementation. Godot Methodology tests whether the same verification principles generalize into software architecture.

[seed-protocol](https://github.com/thisisntjon/seed-protocol) · [thecouncil](https://github.com/thisisntjon/thecouncil) · [bigboss-approval-plane](https://github.com/thisisntjon/bigboss-approval-plane) · [godot-ai-methodology](https://github.com/thisisntjon/godot-ai-methodology) · [simoneresearch.com](https://simoneresearch.com)

Simone Systems Research is founder-led and independent (Jonathan Simone, jon@simoneresearch.com). Principles: Evidence before promotion; Independent verification; Compute must earn its cost; Negative results are retained; Artifacts matter.
