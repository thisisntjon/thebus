# Investigation synthesis — 2026-08-18

Five angles: `interop-standards.md`, `agent-oss.md`, `distributed-systems.md`,
`governance-dissent.md`, `stress-test.md`.

## Verdict on the original hypothesis

**The operator's hypothesis:** others have partially solved this, their ideas are borrowable, and
there is real unclaimed space.

**CONFIRMED on borrowing. REFINED on the space. The effort's unstated premise is
INVALIDATED.**

- *Borrowable ideas:* abundant and concrete — eleven named, most liftable as schema or
  vocabulary without taking a dependency.
- *Real space:* yes, but narrower than assumed. The dissent/quorum gap is the one claim
  that survived every attempt to kill it, confirmed three ways sharing no source.
- *Premise:* the unstated assumption that building fleet infrastructure is the right
  thing to be doing now is closed by the operator's own canon, with an unmet reopen condition.

## The three findings that matter

### 1. The premise was already decided, against

`workflow/canon/DECISIONS.md` in the sibling repository (publication pending), 2026-08-08: *"Default operating mode: fleet or
single agent? → Single strong agent; fleet opt-in for provably independent tickets,"*
because *"30-day fleet campaign produced zero confirmed improvements; multi-agent ~3×
tokens, degrades interdependent work."* Reopen condition: *"An ablation (PLAN P3) shows
the fleet winning on a real task."* P3 is at investigation/plan gate. **Unmet.**

Corroborated externally: MAST (1,600+ traces, 7 frameworks, κ=0.88) ranks the two failure
modes governance addresses — information withholding 0.85%, ignored agent input 1.9% —
dead last of fourteen; specification, verification, and stopping conditions are ~77%.
Anthropic's own multi-agent write-up excludes "domains that require all agents to share
the same context or involve many dependencies," and attributes 80% of performance variance
to token spend rather than architecture.

**Governance is not the binding constraint.**

### 2. The social design is inverted — and this is the substantive finding

thebus was built to *damp* a member's pessimism. Two independent angles say that is
backwards.

- **The targeted failure may not be the real one.** No literature located for "despair
  contagion." The documented pathology is the opposite: false success — 45–48% of
  tau2-bench failures, **75.8% of self-assessing coding-agent trajectories**. Pessimistic
  reports are the *scarce* signal; damping them amplifies the dominant failure.
- **No institution quarantines dissent.** Robert's Rules, judicial dissent, NASA, NIE
  footnotes, Quaker practice, sociocracy — all keep dissent fully readable and strip only
  its *authority*. thebus conflates non-operative with non-visible. Nemeth: dissent
  improves decisions *even when the dissenter is wrong*, so hiding it forfeits that
  unconditionally. Every organizational failure in the corpus failed by **not** surfacing
  dissent.
- **Our exact UI is the measured-worst option.** Steblay's meta-analysis (48 studies):
  never show a dissent under a "disregard this" banner — the hybrid backfires. `bus.py
  orient` prints *"DISSENT REGISTER: 2 open. NOT SHOWN… Do not let it set your priors."*
  That is the banner, verbatim.
- **The symmetric evidentiary bar is the Columbia failure.** CAIB's central finding is
  that NASA *"inverted this burden of proof."* Requiring a dissenter to fund their own
  measurement silences anyone without resources to measure.
- **Independent quorum makes a correct lone dissenter unactionable.** RFC 7282: objections
  must be *addressed*, not counted.

The operator's field observation can be true and the remedy still wrong. The universal replacement
is **binding, not hiding** — attach every dissent to its disposition (rebuttal, status,
date), as NASA binds the dissent memo to management's decision and Wikipedia's WP:PEREN
binds proposals to rebuttals.

### 3. What is genuinely unclaimed

**Model-family heterogeneity as a formal quorum requirement.** BFT assumes independent
failures; two members on the same base model are not two samples. Converges with the
stress-test's surviving finding — cross-family review reduces error >30%, same-family
"little."

Caveat, from two sources: Community Notes' bridging algorithm (matrix factorization,
note-intercept as common ground) is deployed prior art for independence-weighted
consensus, and "Gaming Consensus" (arXiv 2607.01824) attacks it — sybils parked at diverse
latent positions manufacture consensus for ~$30/note. **If you require diversity, an
adversary supplies diversity.** Our echo collapse is under-powered against this: citation
edges do not catch sybils, and forked agents co-locate without citing.

## Conflicts between angles

| conflict | resolution |
|---|---|
| distributed-systems invested in *fixing* leases; stress-test says *delete* seats | Delete for now. Bank the lease findings against P3 reopening the fleet question — they are correct and free to re-apply. |
| stress-test: "despair contagion has no literature"; the operator observed it directly | Not in conflict. Absence of study is not refutation of observation. But governance-dissent independently shows the remedy is wrong regardless of whether the disease is real. |
| interop: gap is real, bespoke justified; stress-test: don't build it | Both hold. The space is real *and* it is not the binding constraint. Space ≠ priority. |
| stray lead vs governance-dissent on Community Notes | Independently corroborated by our own agent (5:1 intercept/factor regularization, Python repo). Promoted from lead to finding. |

## Borrow list (schema/vocabulary only — take no runtime dependency)

The field is consolidating violently: Letta archived its V1 server, AWS handed off
agent-squad, AutoGen and Semantic Kernel self-deprecated into microsoft/agent-framework,
Flowise archived, SuperAGI and MetaGPT dead.

| borrow | from | for |
|---|---|---|
| Passport/Resume/Rule records, open-kind `audit.jsonl` | AG2 `ag2/network` (Apache-2.0) | roster + audit schema |
| `REACHABLE → CLOSED_WORKFLOWS_ONLY → UNREACHABLE` | Temporal | makes "retire this seat yet?" decidable |
| Fencing tokens (sequencers), `lock-delay` | Chubby (2006) | we already mint the token and discard it |
| `LeaseDuration > RenewDeadline > RetryPeriod` | Kubernetes | closes a guaranteed split-brain window |
| SUSPECT state, self-incremented incarnation numbers | SWIM | unambiguous rejoin-after-death |
| Evidence-carrying tallies keyed by signer | BFT | never assert "2 independent"; let readers recount |
| Objection-requires-disposition, `n=1` | RFC 7282 | a correct lone dissenter stays actionable |
| Bind dissent to its disposition | NASA / Wikipedia WP:PEREN | replaces quarantine |
| Right-to-measure; refusal is itself gated | CAIB | uninverts the burden of proof |
| 5:1 intercept/factor regularization | Community Notes (Python, open) | independence weighting |
| Pairwise bonding `k_ij = M/(M+T_ij)`; no reply button | Gitcoin; Polis | sybil resistance; no pile-on |

## What this implies

thebus's *mechanics* borrow well. Its *social design* is inverted. Its *reason to exist
now* is closed by canon. The pieces that survive every angle are: bind-don't-hide,
objection-requires-disposition, right-to-measure, zero-dissents-fails-the-build,
heterogeneity as a quorum requirement, and mechanical detection over agent judgment —
the last because LLM judges detect false success at AUROC 0.54–0.65 (near chance) while
mechanical detectors reach 0.83–0.95.

None of those require a fleet.
