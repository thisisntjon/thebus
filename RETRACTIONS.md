# Retraction ledger

Law 6: correct by editing, retract by ledger. Nothing below is deleted from the history —
the commits stand. This file records what was claimed, what killed it, and what replaced
it, so a reader who encounters the original claim can find its disposition.

All entries dated 2026-08-18, from the five-angle prior-art sweep
(`workflow/research/SYNTHESIS.md`).

---

## R1 — "Dissent should be quarantined from orientation"

**Claimed in:** `PROTOCOL.md` (Two field rules, §2), `README.md`, `AGENTS.md` (rule 3 and
"On morale"), `bus.py` (`quarantine` label, `cmd_orient`, `cmd_dissent_file`).

**Retracted because:** no institution in the surveyed corpus quarantines dissent. Robert's
Rules, judicial dissent, NASA, NIE footnotes, Quaker practice and sociocracy all keep
dissent fully **readable** and strip only its **authority**. thebus conflated
*non-operative* with *non-visible*. Nemeth: dissent improves decisions even when the
dissenter is wrong, so hiding it forfeits that unconditionally.

**Worse — the specific implementation is the measured-worst option.** Steblay's
meta-analysis (48 studies) finds that showing a dissent under a "disregard this" banner
backfires relative to either showing it plainly or not showing it at all. `bus.py orient`
prints exactly that banner: *"DISSENT REGISTER: 2 open. NOT SHOWN… Do not let it set your
priors."*

**Replaced by:** bind, don't hide — attach every dissent to its disposition (rebuttal,
status, date), as NASA binds the dissent memo to management's decision and Wikipedia's
WP:PEREN binds proposals to rebuttals. Specified as Phase 2; **not yet built**.

---

## R2 — "A negative claim carries the same receipt a positive claim does"

**Claimed in:** `PROTOCOL.md` (rule 3), `AGENTS.md` (rule 4), `bus.py`
(`cmd_dissent_file` evidence triad), and recommended in conversation as "the cheapest,
highest-leverage fix."

**Retracted because:** it is the Columbia failure. CAIB's central finding is that NASA
*"inverted this burden of proof."* Requiring a dissenter to fund their own measurement
silences anyone without the resources to measure — which is usually the person best
placed to notice. As shipped, `bus.py dissent file` refuses un-resourced dissent outright.

**Replaced by:** a right-to-measure, whose **refusal is itself a gated event**. Phase 2;
not yet built.

---

## R3 — "Strategy change requires independent quorum"

**Claimed in:** `PROTOCOL.md` (six-dimension table, rule 4), `bus.py` (`cmd_motion`).

**Retracted because:** RFC 7282 — objections must be **addressed**, not counted. Quorum
as the sole gate makes a correct lone dissenter unactionable, which is the failure mode
every dissent-suppression case study turns on.

**Replaced by:** split objection-requiring-disposition (n=1) from motion-to-change-strategy
(n>=N), and let a **met preregistered kill criterion bypass quorum entirely**. Phase 2.

---

## R4 — arXiv 2606.31498 as a load-bearing citation

**Claimed in:** `PROTOCOL.md` (opening), `README.md` (opening).

**Retracted because:** independent primary-spec reads found it wrong in three places, each
flattering to its own thesis. A2A "human escalation: absent" is false —
`INPUT_REQUIRED` and `AUTH_REQUIRED` are exactly that. A2A "audit: absent" is indefensible
against `Task.history`, `historyLength`, `contextId`, `tasks/list` and JWS-signed Agent
Cards, while the paper rates MCP's thinner audit "Partial." ERC-8004 "dissent: absent" is
overstated.

**Replaced by:** cite the primary specs. The gap is real, but it is confirmed by **two**
independent routes — ANP's own non-goals and future-work sections, and an OSS survey
finding zero `quorum`/`dissent` constructs across the field. An invalidated source cannot
serve as a third confirmation, and the earlier "three ways" phrasing is withdrawn.

---

## R5 — "Echo collapse via citation edges is sufficient"

**Claimed in:** `PROTOCOL.md` (rule 2), `bus.py` (`collapse_echo`, `find_earlier_duplicate`).

**Retracted because:** under-powered. Citation edges do not catch sybils, and forked agents
co-locate without ever citing each other. "Gaming Consensus" (arXiv 2607.01824) shows the
general shape of the attack against diversity-based independence: sybils parked at diverse
latent positions manufacture consensus. **If you require diversity, an adversary supplies
diversity.**

**Replaced by:** provenance edges plus prior art not yet evaluated — Community Notes' 5:1
intercept/factor regularization, Gitcoin's pairwise bonding. Phase 0 verifies the sources;
Phase 2 decides. Severity is reduced under the pivot, since 2–3 reviewers is not a fleet.

---

## R6 — "Seats, leases, tombstones, and membership are the thing to build"

**Claimed in:** the whole original design.

**Retracted because:** two reasons, either sufficient. (1) `workflow/canon/DECISIONS.md` in the sibling repository (publication pending)
(2026-08-08) already decided single-agent default, with reopening gated on
an ablation that has not run. (2) MAST ranks the failure modes governance addresses near
the bottom of fourteen; specification and verification dominate. Governance is not the
binding constraint.

**Note:** the *mechanisms* are sound and were improved by the sweep — fencing tokens (we
already mint them and discard them), Kubernetes' `RenewDeadline`, SWIM's SUSPECT state and
incarnation numbers, Chubby's `lock-delay`, Temporal's retirement vocabulary. These are
**banked, not discarded**, and re-appliable if the ablation reopens the fleet question.

---

## What is NOT retracted

- The dissent/quorum gap in the interop protocols is real (two independent confirmations).
- GitHub issues are an adequate provenance substrate.
- GitHub reads lag writes; reconciliation-after-write with a deterministic tie-break is
  required. Verified live, three occurrences.
- Model-family heterogeneity as a formal quorum requirement remains the novelty candidate
  — unproven, and Phase 1 exists to test it.
