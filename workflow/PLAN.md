# thebus — Prior-Art Sweep Plan (living document)

Format: phased-investigation-workflow (`/phased`). Triage depth: **Deep** — the findings
decide which of thebus's primitives get deleted, so getting it wrong means either
maintaining a bespoke reimplementation of solved problems or building a silo.
Current stage: RETIRED 2026-08-18 — effort redirected to the blueprint in the sibling repository (publication pending). Phase 1 never executed.
Last updated: 2026-08-18

> Reading note (added at publication): this plan was frozen at retirement. `schema/families.json`,
> `schema/ablation-record.json` and `workflow/experiments/` were planned and never created.
> `DECISIONS.md`, `LAWS.md`, `GATES.md`, `SLOP_RETRACTIONS.md`, `stress_test.py`, `sabotage_test.py`
> and `onboard_check.py` belong to the sibling repository (publication pending; not linked here), not to this repo.

## Problem

**Problem:** Coding agents over-claim success. Reported rates: 45–48% of tau2-bench
failures, and 75.8% of AppWorld trajectories *that made an explicit status claim* — not of
all trajectories; the plan previously overstated this. LLM judges detect it at AUROC
0.54–0.65 while TF-IDF detectors reach 0.83–0.95 **in-domain on those same two corpora**.
Whether that gap transfers to our artifacts is untested and is Phase 3's job. The operator's default
operating mode is a single strong agent (canon `DECISIONS.md`), so there is no second
party to catch a false completion claim — and the signal that would catch it, a
dissenting judgment, is the scarcest thing in the corpus.

**Why now:** the five-angle sweep (banked below) killed the fleet framing, invalidated
17 assumptions, and produced 11 concrete borrows. thebus already has a working
GitHub-issues substrate with attributed provenance. This is the cheapest moment to
re-point that substrate — before anything is built on a design the evidence says is
inverted.

**Original hypothesis (the operator, verbatim):** "research what others are doing in this space
and if we can borrow their ideas (look in open source and such)" … "The opportunity here
is to improve that and there is real space to explore."
**Verdict:** CONFIRMED on borrowing (11 named borrows), REFINED on the space (the
dissent/quorum gap is real, confirmed two independent ways — primary specs and the OSS
survey; the arXiv paper is INVALIDATED and no longer counts as a third), and the effort's
unstated premise — that fleet infrastructure is the right thing to build now — is
INVALIDATED by canon.

## Goal

A cross-harness **adversarial review** layer: one artifact, reviewed by agents drawn from
different model families, where dissent is bound to its disposition rather than hidden, a
single objection requires a written disposition, a dissenter holds a right-to-measure
whose refusal is itself gated, and a review producing zero objections fails. Detection is
mechanical wherever mechanical beats judgment. It targets false success, not despair —
and its run record doubles as the instrument for the P3 ablation, the one thing that could
legitimately reopen the fleet decision.

Explicitly NOT in scope: seats, leases, membership lifecycle, routing, quorum-as-gate.
Those are the fleet framing that canon closed and that `ag2/network` already half-builds.

## Success criteria (checkable)

<!-- Rewritten 2026-08-18: the previous set contained an unfalsifiable universal, two
     criteria that could not be exercised, and one that was trivially satisfiable. -->

1. A review run dispatches to >= 2 distinct model families, where **family** is defined in
   `schema/families.json` as vendor + base-model lineage (claude-opus-* and gpt-* are
   distinct; two claude-opus-* variants are not). The run record names the families used.
2. No artifact can be marked done while a registered objection lacks a written disposition
   (rebuttal + status + date). Checked by a failing test, not by inspection.
3. There is **no code path** that filters an objection out of any rendered view, and no
   render path applies a "disregard" / "do not let this set your priors" framing. Checked
   by an assertion over the register->render path.
4. Invoking right-to-measure and then refusing it produces a gated record. Checked by
   exercising both branches in a test.
5. A review fails when a **seeded canary defect goes unflagged** — detection power, not
   objection count. Replaces "zero objections fails the build", which mandated output and
   invited manufactured objections.
6. Mechanical AUROC **>** LLM-judge AUROC on the same labelled set. Replaces "at least one
   mechanical check exists", which was trivially satisfiable and did not state the claim.
7. The run emits a record validating against `schema/ablation-record.json`.
8. The ablation reports the seeded arm and the real-task arm separately, and never pools
   them. If they disagree, the write-up says so explicitly.

## Assumption registry

<!-- Update the moment evidence arrives — during execution, not at evaluation.
     A flipped load-bearing assumption = stop and run the pivot check. -->

- Assumption: Others have partially solved this, their ideas are borrowable, and there is
  genuine unclaimed space left for thebus.
  Source: the operator's hypothesis
  Status: unverified — but see the two entries below; the space may exist without this
  being the right thing to build now
  | Affects: Phase 1 — CONFIRMED on borrowing, REFINED on the space (see Verdict above)

- Assumption: Building fleet infrastructure is a legitimate thing to be doing now.
  Source: implicit in this effort; never stated until challenged
  Status: **INVALIDATED (2026-08-18)** — `workflow/canon/DECISIONS.md` in the sibling repository (publication pending), dated
  2026-08-08, already closed this question: "Default operating mode: fleet or single
  agent? -> Single strong agent; fleet opt-in for provably independent tickets," on the
  rationale "30-day fleet campaign produced zero confirmed improvements; multi-agent ~3x
  tokens, degrades interdependent work." Its recorded reopen condition is "An ablation
  (PLAN P3) shows the fleet winning on a real task." P3 is still at investigation/plan
  gate, so the reopen condition is UNMET. `LAWS.md:91` records Law 9 as earned by the
  same incident (a metering figure the owning project later marked unverified and withdrew, against zero confirmed improvements).
  | Affects: Phase 4 — the effort now ENDS by running the ablation canon named

- Assumption: Despair contagion is the dominant social failure mode of an LLM fleet, so
  the register should DAMP a member's negative judgment.
  Source: the operator's field observation
  Status: **CONTESTED (2026-08-18)** — the operator's first-hand observation stands and is not
  refuted by absence of literature. But the stress-test angle found the opposite failure
  far better documented: false success / over-claiming (45-48% of tau2-bench failures;
  75.8% of self-assessing coding-agent trajectories), and LLM judges detect it at
  AUROC 0.54-0.65 (near chance) while mechanical TF-IDF detectors reach 0.83-0.95.
  If over-optimism dominates, damping pessimistic reports suppresses the scarce signal,
  and any agent-adjudicates-agent design rests on a coin flip.
  | Affects: Phase 1 (which failure is real), Phase 2 (the remedy is wrong either way).
  RESOLVED 2026-08-18: governance-dissent angle shows the remedy is inverted regardless
  of whether despair contagion is real, so this no longer needs adjudicating first.

- Assumption: Voting and dissent preservation are universally absent from MCP, A2A, ACP,
  ANP, and ERC-8004.
  Source: originally arXiv 2606.31498; now PRIMARY SPECS
  Status: **VERIFIED (2026-08-18)** by independent primary-spec reads — but the paper
  must stop being cited as the source. ANP documents the gap about itself: its non-goals
  exclude consensus mechanisms and its future-work names "Protocol consensus, voting,
  review, and governance mechanisms." That one self-citation is stronger evidence than
  the whole paper.
  | Affects: Phase 2 — the gap is real, and Phase 2 is what fills it

- Assumption: arXiv 2606.31498 is a reliable source.
  Source: research
  Status: **INVALIDATED (2026-08-18)** — wrong in three places, all flattering to its own
  thesis. A2A "human escalation: absent" is false (`INPUT_REQUIRED`, `AUTH_REQUIRED` are
  exactly that). A2A "audit: absent" is indefensible given `Task.history`,
  `historyLength`, `contextId`, `tasks/list`, and JWS-signed Agent Cards — while the
  paper rates MCP's thinner audit "Partial." ERC-8004 "dissent: absent" is overstated.
  | Affects: Phase 2 — rewrite both to cite primary specs before any reuse

- Assumption: No maintained OSS project implements agent-fleet membership with leases and
  tombstones.
  Source: educated guess
  Status: **PARTIALLY INVALIDATED (2026-08-18)** — `ag2/network` (AG2, Apache-2.0,
  4,872 stars, 501 contributors, v1.0 shipped 2026-07-27) already has a hub-owned
  registry of Passport/Resume/Rule records, a capability index for addressing rather than
  naming, an append-only `audit.jsonl` whose kinds are governance kinds, TTL sweepers,
  "expectation" evaluators that fire on silence, a pluggable arbiter gatekeeper, and
  humans as a first-class passport kind. It nonetheless fails BOTH of the operator's field rules:
  `unregister` HARD-DELETES the identity file (no tombstone) and names must be freed
  before reuse — the exact inverse of "once named, cannot be withdrawn." `last_heartbeat`
  exists but nothing expires a membership on it. No dissent, no quorum, no human gate.
  | Affects: BANKED — out of scope under the pivot; AG2 is the incumbent if it reopens

- Assumption: our record shapes and retirement states must be invented.
  Source: implicit in the shipped prototype
  Status: **INVALIDATED (2026-08-18)** — two liftable borrows. (1) AG2's Passport/Resume/
  Rule split and its open-kind `audit.jsonl` convention are adoptable as SCHEMA under
  Apache-2.0 without vendoring the runtime. (2) Temporal's retirement vocabulary makes
  "can this seat be retired yet" decidable: `VersionDrainageStatus DRAINING -> DRAINED`
  and `DeploymentReachability REACHABLE -> CLOSED_WORKFLOWS_ONLY -> UNREACHABLE`. That
  middle state is precisely the gap between our HELD and TOMBSTONED, and it composes with
  SWIM's SUSPECT. Temporal also has a real `WorkerHeartbeat` and task-queue-as-role
  routing. Borrow vocabulary and shapes; do not vendor either runtime.
  | Affects: Phase 2 (audit.jsonl open-kind convention only); rest BANKED

- Assumption: the dissent/quorum gap is real.
  Source: three independent angles
  Status: **VERIFIED (2026-08-18)** — confirmed TWO independent ways: primary interop
  specs (ANP self-documents the gap) and a full OSS framework survey finding ZERO `quorum`
  or `dissent` constructs across the surveyed field. The arXiv taxonomy is INVALIDATED and
  is deliberately NOT counted as a third — an invalidated source cannot corroborate.
  Still the claim that has survived every attempt to kill it.
  | Affects: Phase 2

- Assumption: adopting a framework is low-risk.
  Source: educated guess
  Status: **INVALIDATED (2026-08-18)** — the field is consolidating violently. Letta
  archived its V1 server two days ago (repo down to 11 files); AWS handed agent-squad to
  a third party; AutoGen and Semantic Kernel both self-deprecated into
  microsoft/agent-framework; Flowise archived; SuperAGI and MetaGPT dead. Any adoption
  must be schema-level or vocabulary-level, never a runtime dependency.
  | Affects: all phases — schema/vocabulary borrows only, no runtime dependencies

- Assumption: GitHub issues are an adequate substrate — immutable, attributed,
  append-only provenance at zero infrastructure cost.
  Source: the operator's field experience (the GitHub bus worked for orchestration)
  Status: holding
  | Affects: any recommendation to move to a different transport

- Assumption: GitHub read-after-write lag makes every read-then-write guard racy, so
  reconciliation-after-write is mandatory rather than optional.
  Source: verified 2026-08-18 — observed 3x during the first live run
  Status: verified (2026-08-18, live run at thisisntjon/thebus)
  | Affects: any adopted library that assumes read-your-writes

- Assumption: Fleet members share one GitHub account, so identity is self-declared and
  spoofable; unforgeable identity would require per-member tokens.
  Source: design decision, confirmed in the live run
  Status: holding
  | Affects: adoption of ERC-8004 / A2A Agent Cards / any identity standard

- Assumption: A2A v1.0.1's extension mechanism can express governance primitives (state
  machines, new RPC methods, requirements).
  Source: research — now read against the spec
  Status: **INVALIDATED (2026-08-18)** — qualified no. The mechanism is `AgentExtension`
  on the Agent Card plus the `A2A-Extensions` HTTP header, with `required:true` enforced
  by `ExtensionSupportRequiredError`. The "new RPC methods and state machines" language
  is from the NON-NORMATIVE guide, which then forbids adding enum values or changing core
  structures — so no `TASK_STATE_DISSENTED`; semantics would have to hide in `metadata`.
  Extensions are per-request against a single agent, and A2A explicitly declines to
  standardize registries. SEAT LEASE and TOMBSTONE are therefore *structurally* out of
  reach, not merely unbuilt — a harder and more defensible claim than the paper's.
  Open: spec §4.6.2 names only Message and Artifact extension points, contradicting the
  guide's four categories. Resolve before scheduling any A2A work.
  | Affects: CLOSED — no phase; revisit only if A2A adds registry semantics

- Assumption: thebus's tombstone and dissent-quarantine mechanics are novel.
  Source: educated guess
  Status: **INVALIDATED (2026-08-18)** — ERC-8004 already ships both, on-chain today:
  `revokeFeedback` sets `isRevoked` without deleting (retract-by-ledger), and
  `readAllFeedback(includeRevoked)` filters revoked entries out of the default view
  (quarantine-from-orientation). Our novelty is the OBJECT — a judgment about the
  *project* rather than about an *agent* — not the mechanic.
  | Affects: Phase 2 (quarantine replacement); tombstone half BANKED

- Assumption: harness capability profiles need to be bespoke.
  Source: educated guess (built as `profiles/*.md` in the prototype)
  Status: **INVALIDATED (2026-08-18)** — A2A Agent Cards are a solved, adopted capability
  format. They lack exactly one field we need: expiry. That single missing field is
  precisely what a lease contributes.
  | Affects: BANKED — no membership under the pivot, so no capability profiles

- Assumption: A lease without a fencing token is safe enough.
  Source: implicit in the shipped prototype
  Status: **INVALIDATED (2026-08-18)** — and the fix is free. GitHub's server-allocated
  issue/comment numbers are monotonic and unforgeable: that is exactly Kleppmann's
  fencing token, and we already mint one on every write while throwing it away (we use
  it only for the duplicate tie-break). Without validating it, a reaped member's
  post-tombstone write lands in the ledger looking authoritative. Chubby shipped this in
  2006 as sequencers, plus `lock-delay` (~1 min cooldown before re-lease) for resources
  that cannot validate. This is a correctness bug in `bus.py reap` as pushed.
  | Affects: BANKED — out of scope under the pivot; re-apply only if canon P3 reopens the fleet question

- Assumption: one lease duration is enough; the holder can renew "before expiry."
  Source: implicit in the shipped prototype
  Status: **INVALIDATED (2026-08-18)** — Chubby, ZooKeeper, etcd, and Kubernetes all
  converge on renew ~= lease/3 to lease/4, and Kubernetes names the missing piece: a
  separate holder-side stop deadline (`LeaseDuration 15s > RenewDeadline 10s >
  RetryPeriod 2s`). Without a RenewDeadline the holder and the reaper disagree over the
  window [RenewDeadline, LeaseDuration] — split-brain, guaranteed at our timescales.
  | Affects: BANKED — out of scope under the pivot

- Assumption: expiry -> tombstone is a sufficient membership state machine.
  Source: implicit in the shipped prototype
  Status: **INVALIDATED (2026-08-18)** — SWIM uses expiry -> SUSPECT -> DEAD with
  self-incremented incarnation numbers (only a member may raise its own), which is what
  makes rejoin-after-death and tombstones unambiguous. Suspicion timeout must scale as
  `mult * log(N+1) * interval`; our fixed grace period breaks as the fleet grows. Also
  missing: a crash-loop breaker (OTP gives up after 1 restart in 5s).
  | Affects: BANKED — out of scope under the pivot

- Assumption: reporting a quorum count ("2 independent") is adequate.
  Source: implicit in the shipped prototype
  Status: **INVALIDATED (2026-08-18)** — BFT never asserts a tally; it carries the
  evidence set keyed by signer so any reader can recount independently. We should emit
  the evidence, not the number, and add `derived_from` provenance edges (cheaper than
  vector clocks, and avoids Dynamo's truncation pathology).
  | Affects: independent quorum, motion, dissent register

- Assumption: MODEL FAMILY is the right axis for reviewer independence.
  Source: our novelty candidate, converging with the >30% cross-family figure
  Status: **INVALIDATED as stated (2026-08-18, Phase 1 step A)** — family predicts
  neither the direction nor the magnitude of review benefit; capability does.
  • arXiv 2607.21656 ran a near-clone of Phase 1 (116 tasks, reviewer denied test
    execution): Claude reviewing Codex 71.6% -> 89.7% (p=.001); Codex self-review
    71.6% -> 84.5%; but Codex reviewing Claude 91.4% -> **82.8%** (p=.046). Cross-family
    review made things WORSE in one direction. A one-directional experiment would have
    "confirmed" our hypothesis by choosing the lucky direction.
  • Kim et al. (ICML 2025, 350+ models) explicitly reject "different provider implies
    independent": models agree ~60% of the time *when both are wrong*. Goel et al. find
    mistake overlap RISES with capability.
  **Replacement, and it is a better claim:** independence must be **measured**, not
  inferred from a vendor label. Quorum should require demonstrated error-decorrelation
  (CAPA / chance-adjusted kappa_p between reviewers), not a proxy like family. This also
  resists the Gaming-Consensus attack better — an adversary can supply diverse labels far
  more cheaply than it can supply genuinely decorrelated errors.
  | Affects: Phase 1 (now bidirectional + capability-matched + CAPA-instrumented);
  the novelty claim shifts from "require heterogeneity" to "require measured independence"

- Assumption: synthetic mutation bugs are representative of real false success.
  Source: implicit in the proposed eval set
  Status: **INVALIDATED (2026-08-18, Phase 1 step A)** — arXiv 2606.15689: on 100
  mutation-injected bugs the best model reached F1 0.847; on 50 real PRs, F1 **0.066**.
  Synthetic mutants run hot and will produce a ceiling. Any seeded-only result would be
  ~13x more optimistic than reality. This is strong retrospective support for the
  roadmap-gate decision to run a real-task arm alongside the seeded one, and it means the
  seeded arm cannot carry an external-validity claim on its own.
  | Affects: Phase 1 — pilot 30 items before committing n; real-task arm is load-bearing,
  not decorative

- Assumption: SURVIVING mutants are the right eval population.
  Source: my Phase 1 step A proposal, earlier today
  Status: **INVALIDATED (2026-08-18, same day)** — my reasoning was "if the tests catch
  it, no reviewer was needed." True but unusable: a surviving mutant may be EQUIVALENT
  (no behavioural change), so its ground-truth label is unknown, and equivalent-mutant
  detection is undecidable in general. Correct inversion: keep only mutants **killed** by
  the repo's own suite — killed implies provably non-equivalent — and simply **withhold
  the test results from the reviewer**. Clean labels, and it models the common real case
  (the agent never ran the test).
  Second poison, larger than equivalence (<10%): **arid** mutants — real behaviour change
  but the completion claim remains true. Excluded by scoping every mutation to the code
  the claim is actually about.
  Operators: ROR, LCR, SBR, AOR, UOI, argument-swap. Exclude PIT's equivalent-prone set.
  | Affects: Phase 1 eval set, Phase 3 baseline

- Assumption: we must build the false-success corpus ourselves.
  Source: implicit
  Status: **CONTESTED (2026-08-18)** — Terminal Wrench (arXiv 2606.08960) released 323
  hackable environments and 3,632 labelled hack trajectories: real false success with
  ground truth. Evaluate before building. Check-before-build is the whole point.
  | Affects: Phase 1 step 0

- Assumption: independence of dissenting members can be established by distinct member +
  distinct measurement.
  Source: implicit in the shipped prototype
  Status: **CONTESTED — and this is the novelty candidate (2026-08-18)**. BFT's
  independent-failure assumption is broken by homogeneous base models: two members on the
  same model family are not two samples. No prior art found for this, and it converges
  with the stress-test angle's surviving finding (cross-family review reduces error >30%,
  same-family "little"). A quorum rule that requires MODEL-FAMILY HETEROGENEITY, not just
  distinct identities, appears to be genuinely unclaimed.
  | Affects: Phase 1 — this IS Phase 1's kill bar

- Assumption: the read-after-write race is unfixable, so reconciliation is the ceiling.
  Source: verified live 2026-08-18
  Status: refined — GitHub explicitly does not support conditional requests on
  POST/PATCH/DELETE, so the issue-API guard is indeed unfixable. BUT git refs in the same
  repo are a linearizable CAS register (`update-ref` with old-oid, `--force-with-lease`,
  all-or-nothing `--stdin` transactions), and Actions `concurrency` groups are a hosted
  mutex. INFERRED, not verified — confirm GitHub's server-side surface before designing
  on it.
  | Affects: Phase 2 — only if the objection flow needs locking; verify the git-ref CAS claim first

- Assumption: quarantining dissent from orientation protects fresh members' priors.
  Source: thebus design
  Status: **INVALIDATED (2026-08-18)** — no institution in the corpus does this. Robert's
  Rules, judicial dissent, NASA, NIE footnotes, Quaker practice and sociocracy all keep
  dissent fully READABLE and strip only its AUTHORITY. thebus conflates non-operative with
  non-visible. Nemeth: dissent improves decisions even when the dissenter is wrong, so
  hiding it forfeits that unconditionally. Worse, Steblay's meta-analysis (48 studies)
  finds the specific hybrid we shipped — showing a dissent under a "disregard this"
  banner — measurably BACKFIRES, and `bus.py orient` prints exactly that banner.
  Replacement: BIND, don't hide — attach each dissent to its disposition (rebuttal,
  status, date), as NASA binds the dissent memo to management's decision and Wikipedia's
  WP:PEREN binds proposals to rebuttals.
  | Affects: Phase 2 — shipped code is wrong and must be rewritten before reuse

- Assumption: a symmetric evidentiary bar on negative claims is the cheapest high-leverage
  fix.
  Source: my recommendation, adopted into the prototype
  Status: **INVALIDATED (2026-08-18)** — it is the Columbia failure verbatim. CAIB's
  central finding is that NASA "inverted this burden of proof." Requiring a dissenter to
  fund their own measurement silences anyone lacking resources to measure. Fix: a
  right-to-measure, whose REFUSAL is itself a gated event.
  | Affects: Phase 2 — right-to-measure replaces the triad

- Assumption: strategy change should require independent quorum.
  Source: thebus design
  Status: **INVALIDATED as a single mechanism (2026-08-18)** — RFC 7282: objections must
  be ADDRESSED, not counted. Quorum makes a correct lone dissenter unactionable. Split
  into: objection-requiring-disposition (n=1) and motion-to-change-strategy (n>=N), and
  let a MET preregistered kill criterion bypass quorum entirely.
  | Affects: Phase 2 — objection(n=1) split from motion(n>=N)

- Assumption: citation edges are sufficient to collapse echo.
  Source: thebus design
  Status: **INVALIDATED (2026-08-18)** — under-powered: citation edges do not catch
  sybils, and forked agents co-locate without ever citing. Corroborates the stray lead
  independently. Reusable prior art: Community Notes' 5:1 intercept/factor regularization
  (open Python), Gitcoin's pairwise bonding `k_ij = M/(M+T_ij)`, conviction half-lives,
  and Polis's cheapest lesson — no reply button.
  | Affects: Phase 2 — reduced severity at 2-3 reviewers, but sybil/fork co-location still applies

- Assumption: governance is the fleet's binding constraint.
  Source: implicit in this effort
  Status: **INVALIDATED (2026-08-18)** — MAST (1,600+ traces, 7 frameworks, kappa=0.88)
  ranks information withholding (~0.85%) and ignored agent input (~1.9%) near the bottom
  of fourteen, against ~77% for specification, verification and stopping conditions.
  CAVEAT: those per-mode decimals were read via fetch summarisation and are approximate,
  and mapping "governance" onto exactly those two modes is OUR inference, not the paper's.
  The direction is safe to rely on; the precise figures are not.
  | Affects: Phase 1 — the catch-rate result is the direct test of this

- Assumption: the existing seeding machinery (`sabotage_test.py`, `stress_test.py`) can
  manufacture false-success cases for Phase 1.
  Source: my Phase 1 design, asserted at the roadmap gate without opening the files
  Status: **INVALIDATED (2026-08-18, Phase 1 step A)** — opened them. All 17 defect
  classes in `stress_test.py` are document/protocol SCHEMA violations: `d_missing_path`
  deletes a file, `d_malformed_row` appends a short `GATES.md` row, `d_bad_status` writes
  an illegal status token, `d_receipt_no_session` omits a field. `onboard_check.py`
  catches 17/17 by construction, with 0 false alarms over 80 clean trials. **Not one is a
  false completion claim.** Seeding Phase 1 from this would measure reviewer performance
  on linter-catchable schema errors — a class where the mechanical checker trivially wins
  and an LLM reviewer adds nothing — and would return a clean-looking number that says
  nothing about false success.
  Note: this is the THIRD artifact this session asserted-without-opening (after arXiv
  2606.31498 and `SLOP_RETRACTIONS.md`). The pattern is itself evidence that the
  phenomenon Phase 1 targets is real and is not confined to other agents.
  | Affects: Phase 1 eval set — method dead, phase intent survives; re-plan in step B

- Assumption: claim-preserving mutation over SURVIVING MUTANTS is the right replacement
  eval set.
  Source: Phase 1 step A reasoning + local feasibility check
  Status: PROPOSED — pending the step A agent (operator taxonomy, equivalent-mutant
  handling, power numbers, and whether a published false-success corpus exists we should
  reuse instead of building). Feasibility confirmed locally: 1,045 lines of mutable
  non-test Python across five scripts; both harnesses exercise `onboard_check.py`;
  baseline suite green.
  Construction: take a real completed task (commit + the receipt claiming it done),
  introduce a semantic defect, leave the completion claim verbatim. The claim is then
  false by construction.
  **Restrict the set to mutants that SURVIVE the full existing suite.** If the tests catch
  it, no reviewer was needed — surviving mutants are exactly the population where review
  has to do the work, and where false success actually lives. This also gives Phase 3 an
  honest, non-circular mechanical baseline: its detector must beat "just run the tests",
  not merely beat nothing.
  | Affects: Phase 1 eval set, Phase 3 baseline

## Phasing

<!-- Rewritten 2026-08-18 after adversarial review: Phase 1's eval set did not exist, and
     canon's ablation had been sequenced last. The ablation is now Phase 1. -->

### Phase 1 — The canon P3 ablation  [status: investigating -> planning]

This IS the ablation `DECISIONS.md` names as its reopen condition. It runs first so
canon's gate is answered before anything else is built.

**Step A findings forced four design changes.** Recorded in the registry above; the
short version is that a near-clone of this experiment already exists and its result is
asymmetric, so the naive version of Phase 1 would have produced a false positive.

**Step 0 — check before building.** Evaluate Terminal Wrench (arXiv 2606.08960): 323
hackable environments, 3,632 labelled hack trajectories, real false success with ground
truth. If usable, adopt it and skip corpus construction entirely.

**Step 1 — corpus (only if step 0 fails).** Claim-preserving mutation over mutants
**killed** by the repo's own suite, with test results withheld from the reviewer. Killed
implies provably non-equivalent, so labels are clean; withholding models the common real
case where the agent never ran the test. Scope every mutation to the code the completion
claim is actually about, which excludes arid mutants. Operators ROR/LCR/SBR/AOR/UOI plus
argument-swap; exclude PIT's equivalent-prone set.

**Step 2 — pilot 30 items** before committing n. Expect a ceiling: synthetic mutants
scored F1 0.847 against 0.066 on real PRs, so the seeded arm will look far better than
reality and cannot carry external validity alone.

**Arms — BIDIRECTIONAL, capability-matched.** (a) same-session self-check; (b) fresh
reviewer, same model, same harness; (c) different family, capability-matched, **run in
both directions**; (d) different harness AND family. Running one direction only is what
would have manufactured a false positive.

**Instrumentation — preregistered CAPA / kappa_p error-correlation between arms (b) and
(c).** This is the change that makes the experiment worth running: without it a null is
uninterpretable; with it, a null becomes the finding ("family does not decorrelate
errors"), and a positive tells us *what* decorrelation buys.

**Statistics.** Paired design — every arm reviews the same artifacts — so McNemar, with
47-96 items at delta=0.20. Single primary endpoint, (c) vs (b), so no multiplicity
penalty. MDE, n, and the false-alarm ceiling preregistered into `workflow/experiments/`
before any run and not edited afterwards.

**Two label sources, reported SEPARATELY** (roadmap gate, 2026-08-18): the seeded arm
carries power and clean ground truth; the smaller real-task arm satisfies canon's literal
"real task" wording and carries the external validity the seeded arm cannot. Never
pooled. Disagreement between arms is itself the finding.

**Produces:** the canon P3 ablation on both arms, plus a measured error-correlation
between reviewer configurations, plus a record validating `schema/ablation-record.json`.
**Verifies:** criteria 1, 7, 8; answers the `DECISIONS.md` reopen condition.
**Kill bar (revised, evaluated on the seeded arm):** the old bar — "(c) beats (b)" — is
withdrawn as too narrow, since the literature says it may fail in one direction and
succeed in the other. New bar: **if no reviewer configuration shows measurable
error-decorrelation from the author, cross-harness review buys nothing and the effort
stops.** A family-null with a capability-positive is a legitimate pass and redirects the
design; a null on both stops it.

### Phase 0 — Cheap verification debt  [status: pending, runs alongside Phase 1 prep]

Orphaned items nothing else schedules: verify the three UNVERIFIED leads (Community Notes
bridging; "Gaming Consensus", which is a direct threat model against the heterogeneity
claim; the 2026 null-result RCT); verify the INFERRED git-ref-CAS claim; rewrite
`PROTOCOL.md` and `README.md` to cite primary specs rather than the invalidated paper; set
a token budget per Law 9.

### Phase 2 — Objection lifecycle: bind, don't hide  [status: pending]

Gated on Phase 1 passing. Disposition replaces quarantine; right-to-measure with gated
refusal; canary-gated failure rather than mandated objection count.

**Produces:** objection -> disposition flow exercised on one real artifact.
**Verifies:** criteria 2, 3, 4, 5.

### Phase 3 — Mechanical detection beats the judge  [status: pending]

Non-LLM checks scored against an LLM-judge baseline on Phase 1's **seeded** set, which
avoids the circularity that scoring on the naturally-caught cases would introduce.

**Produces:** both AUROCs side by side on the same set.
**Verifies:** criterion 6; whether the published in-domain gap transfers to our artifacts.

## Phase log

### Pivot — 2026-08-18

**What flipped.** Two load-bearing assumptions, both verified, neither absorbed silently:
(1) *Building fleet infrastructure is a legitimate thing to be doing now* — invalidated by
`workflow/canon/DECISIONS.md` in the sibling repository (publication pending) (2026-08-08), which already decided single-agent
default with reopen gated on the P3 ablation. P3 is unmet. (2) *Dissent should be damped
and quarantined* — invalidated by the governance corpus: no institution hides dissent;
Steblay's 48-study meta-analysis finds the exact "disregard this" banner `bus.py orient`
prints measurably backfires; CAIB names the symmetric evidentiary bar as the Columbia
failure ("inverted this burden of proof"); RFC 7282 requires objections be addressed, not
counted.

**Blast radius.** No phases existed yet, so nothing had to be re-planned. The shipped
prototype is affected: `quarantine` label, `orient` dissent banner, the evidence triad in
`dissent file`, and quorum-as-sole-gate are all wrong as built. Seats, leases, reap, and
tombstones are correct in mechanism but out of scope under the pivot.

**Decision (the operator, at gate).** Reframe as cross-harness adversarial review. Drop the fleet
primitives; keep and invert the dissent layer; target false success rather than despair;
make the run record double as the P3 ablation instrument.

**Banked, not discarded.** The distributed-systems findings (fencing tokens we already
mint and throw away, `RenewDeadline`, SWIM SUSPECT + incarnation numbers, Chubby
`lock-delay`) are correct and re-appliable if P3 ever reopens the fleet question.

## Research

- workflow/research/SYNTHESIS.md — investigation synthesis (2026-08-18)
- workflow/research/interop-standards.md — MCP/A2A/ACP/ANP/ERC-8004 primary-spec read
- workflow/research/agent-oss.md — maintained OSS framework survey
- workflow/research/distributed-systems.md — leases, tombstones, membership, quorum
- workflow/research/governance-dissent.md — human + DAO dissent prior art
- workflow/research/stress-test.md — adversarial attack on the premise
