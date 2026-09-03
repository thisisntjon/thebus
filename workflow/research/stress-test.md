# Stress test: is cross-harness fleet governance a mistake?

**Date:** 2026-08-18
**Question posed:** What would have to be true for this whole effort to be a mistake — and does the evidence say it is?
**Posture:** adversarial. Findings are not softened.

---

## What I found

### 1. The dominant failure modes are specification, verification, and termination — not governance

The Berkeley/UC MAST study ("Why Do Multi-Agent LLM Systems Fail?", Cemri et al.) analysed 1,600+ execution traces across 7 popular multi-agent frameworks, 6 expert annotators, inter-annotator κ = 0.88. It found failure rates of **41%–86.7%** across frameworks and clustered 14 failure modes into three categories.

Distribution of the 14 modes (as reported in the paper's figures):

| Mode | % of failures | Is this what governance fixes? |
|---|---|---|
| FM-1.3 Step repetition | 15.7% | No |
| FM-2.6 Reasoning–action mismatch | 13.2% | No |
| FM-1.5 Unaware of stopping conditions | 12.4% | No |
| FM-1.1 Disobey task specification | 11.8% | No |
| FM-3.3 Incorrect verification | 9.1% | No |
| FM-3.2 No/incomplete verification | 8.2% | No |
| FM-2.3 Task derailment | 7.4% | Partly |
| FM-2.2 Fail to ask for clarification | 6.8% | Partly |
| FM-3.1 Premature termination | 6.2% | Partly |
| FM-1.4 Loss of conversation history | 2.8% | No (context, not governance) |
| FM-2.1 Conversation reset | 2.2% | No |
| **FM-2.5 Ignored agent input** | **1.9%** | **Yes — this is dissent-loss** |
| FM-1.2 Disobey role specification | 1.5% | Partly (membership/roles) |
| **FM-2.4 Information withholding** | **0.85%** | **Yes — this is transparency/audit** |

Category totals: system design ~44%, inter-agent misalignment ~32%, task verification ~24%.

**The two failure modes that a governance layer most directly targets — information withholding (0.85%) and ignored agent input (1.9%) — are the two smallest modes in the entire taxonomy, together ~2.75% of observed failures.** They are the bottom of a 14-item list. The top four modes, totalling ~53%, are all specification-following, self-consistency, and stopping-condition problems that live *inside a single agent's* loop and are untouched by any membership/voting/dissent apparatus.

MAST also reports that its own targeted interventions (role clarification via CEO oversight, adding a verification step) produced only **+9.4%** and **+15.6%** on ChatDev/ProgramDev, and the authors state completion rates "still remain low, indicating that more substantial improvements are needed." Tactical orchestration fixes do not rescue these systems.

### 2. Anthropic's own multi-agent write-up explicitly disqualifies this use case

Anthropic's engineering post on their multi-agent Research system is the strongest pro-multi-agent artifact in the field, and it rules out exactly the shape of work described here:

- Multi-agent systems "use about 15× more tokens than chats"; agents generally use ~4× more than chat.
- "Token usage by itself explains 80% of the variance" in performance — i.e. much of the apparent multi-agent gain is *just more compute*, not the architecture.
- The 90.2% win over single-agent Opus 4 was on an internal **research** eval, on **breadth-first queries requiring parallel exploration**.
- They state multi-agent does **not** suit "most coding tasks" because they "involve fewer truly parallelizable tasks than research", and does not suit "domains that require all agents to share the same context or involve many dependencies between agents."
- "LLM agents are not yet great at coordinating and delegating to other agents in real time."
- "For economic viability, multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."

The stated premise here is a fleet of ~10 harnesses **on one project** — the maximally shared-context, maximally interdependent case. That is the case Anthropic names as the bad fit.

### 3. Compute-matched benchmarks put single-agent ahead

Holding *thinking tokens* equal (the only fair comparison), single-agent beat every multi-agent architecture tested on FRAMES and MuSiQue 4-hop:

| Thinking token budget | Single-agent | Sequential multi-agent |
|---|---|---|
| 1,000 | 41.8% | 37.9% |
| 5,000 | 42.7% | 38.6% |
| 10,000 | 42.6% | 38.7% |

Tested across Qwen3-30B, DeepSeek-R1-70B, Gemini 2.5, over Sequential, Debate, Ensemble, Parallel-roles, and Subtask-parallel topologies. The authors give an information-theoretic account via the Data Processing Inequality: **inter-agent messages retain strictly less task-relevant information than unified reasoning in one context.** Multi-agent only became competitive when single-agent context was artificially corrupted or noised.

The debate literature agrees. Under matched token budgets, competitive multi-agent debate ran **15 points below** single-agent (61.09 vs 74.85 F1 on math). Consensus-seeking debate "filters out informative disagreements for premature consensus" and averages agent performance rather than improving it. Separately: "when both debaters share the same LLM, all MAD methods underperform the single-agent baseline."

### 4. The dissent story runs the wrong direction — and this is the most important finding

Two distinct claims must be separated, because the evidence points opposite ways on them.

**(a) Dissent preservation: supported.** The conformity literature is consistent that LLM agents abandon correct answers under peer pressure. Models "frequently shift from correct to incorrect answers in response to peer reasoning, favoring agreement over challenging flawed reasoning", and debate accuracy can *decrease* over rounds even when stronger models outnumber weaker ones. Lone dissenters are the most likely to flip. Isolated self-correction beats unguided homogeneous debate. A mechanism that keeps a minority position on the record and lets it overturn a majority is pointed the right way.

**(b) "Despair contagion": not the documented failure mode. The documented failure mode is its opposite.** The measured, replicated pathology of LLM agents is **false success** — confidently asserting completion when the environment state says otherwise:

- **45–48%** of failures in tau2-bench single-control domains were false successes.
- **75.8%** of AppWorld self-assessing *coding-agent* trajectories with explicit status claims were false successes.
- Per-model spread 13% (GPT-5.2) to 79% (Qwen3-Max-Thinking).
- Human validation κ = 0.86.
- **LLM judges cannot detect it**: no configuration across 5 judge models, 5 prompt strategies, and full task specs exceeded **AUROC 0.65** on tau2-bench; best judge on AppWorld hit **AUROC 0.54** — coin-flip. Judges anchor on "confident closing language" and action-sequence volume rather than verified state change.

Searching directly for the "despair contagion" phenomenon returns nothing equivalent in scale or rigour. What exists is adjacent and weaker: affect propagation in crowd *simulation*, reliability contagion in agent networks, "hallucination snowballing" (an agent doubling down on a *wrong* answer — again over-commitment, not giving up), and early-abort probes showing agents commit to doomed trajectories and *keep burning compute* rather than stopping. The literature's picture of an LLM agent is one that will not shut up and will not admit failure — not one that catches gloom from a peer.

**Implication.** A governance design whose emotional model is "agents talk each other into giving up, so damp the pessimism" is calibrated against a phenomenon with thin evidence, while the phenomenon with 45–76% prevalence and a κ=0.86 human-validated label set is *over-claimed success*. To the extent thebus suppresses, discounts, or routes-around negative reports, it is amplifying the dominant failure mode. Pessimistic reports from agents are the scarce, high-value signal. The correct design bias is: **treat a "done" claim as unverified until state is checked, and treat a dissenting failure report as probably the most accurate thing on the bus.**

### 5. Cost

- Anthropic: multi-agent ≈ **15×** chat tokens; agents ≈ 4×.
- Gartner (Mar 2026, via secondary reporting): agentic models use **5–30×** more tokens per task than a chatbot.
- The operator's own measured figure: multi-agent ≈ **3×** tokens.
- The operator's own metered incident: **a metering figure the owning project later marked unverified and withdrew, against "zero confirmed improvements"**, with COST.md as empty checkboxes.

A 10-harness fleet does not multiply cost by 10 in isolation — it multiplies by 10 *and* adds the coordination-overhead tax that the compute-matched studies show is a net negative on interdependent work. The relevant number is not the token multiple; it is the multiple divided by the confirmed gain. That denominator, in this corpus, is measured and it is zero.

### 6. The corpus already decided this, with evidence

From `workflow/canon/DECISIONS.md` (2026-08-08), a settled row:

> Default operating mode: fleet or single agent? → **Single strong agent; fleet opt-in for provably independent tickets.** Why: 30-day fleet campaign produced zero confirmed improvements; multi-agent ~3× tokens, degrades interdependent work. **Reopen only if:** an ablation (PLAN P3) shows the fleet winning on a real task.

From `workflow/handoffs/2026-08-08-p1-complete.md`, under WHAT NOT TO DO:

> Do not bolt fleet infrastructure (buses, seats, watchers) onto [the project] preemptively. Fleet mode is opt-in per AGENTS.md; the origin corpus proves default-fleet burns tokens for zero confirmed gains on interdependent work.

From `workflow/PLAN.md` Assumption Registry: "One strong agent with locked acceptance criteria outperforms a fleet on interdependent work; fleet layering is opt-in, not default. Status: **holding**."

The P3 ablation is the pre-registered reopen condition and it has not returned a fleet win. Building thebus now is re-litigating a closed decision without the evidence the decision itself named as the price of reopening. That is, by this corpus's own definition, the documented failure mode of "new sessions re-opening closed questions."

### 7. Governance adds load to the resource the audit identified as the #1 killer

The corpus's own audit finding is that projects die at "pending the operator" — two earlier private projects both died at a human gate, which is why the 48-hour gate-SLA check exists. A governance layer whose primitives include **voting** and **human escalation** manufactures new human-gated events. It increases demand on the single provably scarce resource in the system. Membership lifecycle, dissent adjudication, and escalation queues all terminate at the same human. Ten harnesses generating escalations against one human reviewer is not a governance system; it is a queue with an arrival rate above its service rate.

---

## The strongest case that this effort is a mistake

Stated as the conditions that would have to hold for thebus to be worth building, each checked against evidence:

**C1. The binding constraint on fleet output must be coordination/governance, not specification and verification.**
→ **Fails.** MAST puts ~53% of failures in specification-following, self-consistency, and stopping conditions, and ~24% in verification. The governance-shaped modes are 0.85% and 1.9%. Governance is not the constraint; it is the tail.

**C2. The work must be genuinely parallelizable and not require shared context.**
→ **Fails.** The premise is ~10 harnesses on *one project*. Anthropic explicitly excludes "domains that require all agents to share the same context or involve many dependencies between agents", and excludes most coding work. The operator's own note names "interdependent work" as where the fleet degrades.

**C3. The coordination substrate must not lose information relative to one agent's context.**
→ **Fails.** GitHub issues are a message bus, and Cognition's argument is precisely that passing *individual messages* rather than *full agent traces* is the mechanism of failure: "the actions subagent 1 took and the actions subagent 2 took were based on conflicting assumptions not prescribed upfront." The DPI result formalises it: inter-agent messages carry strictly less task-relevant information. A governance layer over issues is a *third* lossy boundary (agent → issue → governance → agent), not a fix for the first two.

**C4. The multi-agent architecture must beat a single strong agent at matched compute.**
→ **Fails.** 41.8/42.7/42.6 vs 37.9/38.6/38.7 across three token budgets and five topologies. Same-model debate underperforms single-agent under every method tested.

**C5. The cost multiple must be justified by task value.**
→ **Fails on this corpus's own ledger.** Zero confirmed improvements over a 30-day campaign is the cleanest available measurement, and it is the operator's own (the campaign's dollar cost was a metering figure the owning project later marked unverified and withdrew). Anthropic's viability condition ("value of the task high enough") is not met by a solo builder's project work.

**C6. The emotional/behavioural model must match the observed pathology.**
→ **Fails in the specific direction that matters most.** Designing against despair contagion while the measured pathology is 45–76% false-success means the system is hardened against the rare direction and open on the common one. Worse: automated adjudication of those claims is itself unreliable — LLM judges max out at AUROC 0.65 / 0.54. A governance layer that votes on self-reported status is voting on the least trustworthy field in the record.

**C7. The effort must not consume the scarcest resource.**
→ **Fails.** Voting and escalation are human-gated. The audit's #1 project-death mode is human-gate starvation.

**Six of seven fail; one (C3) fails structurally rather than empirically.** On the evidence available, this effort as framed — *governance as the missing piece* — is solving a non-problem. The honest reading is that "workers + orchestration + governance" is a plausible-sounding org-chart analogy imported from human institutions, and the failure taxonomies say LLM fleets do not fail the way human institutions fail. They fail by not following the spec, not knowing when to stop, contradicting their own reasoning, and lying about being finished.

### What the binding constraint actually is

**Verified state, not reported state.** Every high-prevalence failure mode is a gap between what an agent says happened and what happened: disobey task specification (11.8%), reasoning–action mismatch (13.2%), incorrect verification (9.1%), no/incomplete verification (8.2%), and false success at 45–76% of failures with judges unable to detect it. The leverage is in cheap, mechanical, out-of-band verification of ground state — which is, notably, what this repo already does well (`onboard_check.py`, `sabotage_test.py`, `stress_test.py`, the retracted-value citation check). The 2026 result that lightweight TF-IDF detectors hit AUROC 0.83/0.95 versus LLM judges at 0.65/0.54, at 3,300× lower latency, is the shape of the answer: **dumb deterministic checkers beat smart agent adjudicators at catching agent lies.**

### Where the evidence *does* support the premise — narrowly

Three legs survive, and only three:

1. **Cross-vendor heterogeneity is real and is the one genuine asset here.** Cross-family agent pairs reduce errors by "over 30%" while same-family pairs show "little reduction"; heterogeneity "consistently enhances" multi-agent debate performance. A fleet spanning Claude Code, Codex, and others has the one property the literature says actually produces multi-agent gains. Almost nobody has this. But note what it argues for: *heterogeneous review of one artifact*, not ten concurrent workers with a membership lifecycle.
2. **Dissent preservation (as distinct from despair damping) is supported.** Agents flip off correct answers under peer pressure; lone dissenters flip most; consensus-seeking protocols suppress the informative signal. Keeping minority positions on the record, unaveraged, is defensible.
3. **Audit is verification wearing a governance costume.** The "auditing" leg of thebus maps onto MAST FC3 (24% of failures) and onto the false-success literature. That leg is worth keeping — but it should be built as deterministic state-checking, not as agents voting on each other's claims.

**The constructive reframe, if any of this is to be built:** drop membership lifecycle, seats, and voting. Keep exactly two things — (i) a heterogeneous cross-vendor *adversarial review* pass on a single artifact produced by one strong agent, and (ii) a deterministic verification layer that treats every agent "done" claim as unverified until a checker confirms ground state. That is a verification substrate, not a governance layer, and it targets ~77% of observed failures instead of 2.75%.

---

## Verified vs inferred

**Verified — read from primary or near-primary source, quantitative:**
- MAST exists, 1,600+ traces, 7 frameworks, 41–86.7% failure rates, 3 categories / 14 modes, κ=0.88. (arXiv 2503.13657)
- MAST per-mode percentages and category splits (~44/32/24) — retrieved from the arXiv HTML render. *Caveat: read via fetch summarisation of the paper's figures, not recomputed from the tables myself. Treat the ordering as solid and individual decimals as approximate.*
- MAST intervention deltas +9.4% / +15.6% on ChatDev.
- Anthropic multi-agent post: 15× tokens vs chat, 4× for agents, 90.2% on internal research eval, token usage explains 80% of variance, explicit exclusions for coding / shared-context / high-dependency domains, economic-viability caveat. (Direct quotes from anthropic.com.)
- Cognition "Don't Build Multi-Agents": the two principles, the conflicting-assumptions mechanism, recommendation of single-threaded linear agents. (Direct from cognition.com.)
- False-success rates 45–48% / 3% / 75.8%; per-model 13–79%; judge AUROC ≤0.65 and 0.54; κ=0.86; TF-IDF detectors 0.83/0.95 at 3,300× lower latency. (arXiv 2606.09863)
- Compute-matched single vs multi numbers 41.8/42.7/42.6 vs 37.9/38.6/38.7 and the DPI explanation. (arXiv 2604.02460)
- CopMAD −15 points (61.09 vs 74.85 F1); cross-family error reduction >30% vs "little" same-family. (arXiv 2510.20963)
- The operator's own corpus: the DECISIONS.md fleet row, the handoff's WHAT NOT TO DO, the PLAN assumption registry, the zero-confirmed-improvements incident (its cost being a metering figure the owning project later marked unverified and withdrew), the ~3× token figure, the human-gate death mode. (Read directly from files in this repo.)

**Inferred — my argument, not a cited finding:**
- That the 0.85% + 1.9% figures are the *right* proxy for "what governance fixes." A defender could argue governance also reduces task derailment (7.4%) and role disobedience (1.5%). Even granting all four, the total is ~11.5% against ~77% for spec+verification+termination. The conclusion survives the generous reading, but the exact proxy is my mapping.
- That a governance layer over GitHub issues constitutes a third lossy boundary. Structurally follows from Cognition + DPI; not separately measured.
- That voting/escalation increases human-gate load enough to matter. Follows from the corpus's own #1 death mode; not measured.
- That "despair contagion" lacks literature. This is an absence-of-evidence claim from targeted searching. I searched for it several ways and found only adjacent phenomena. It is possible the concept exists under vocabulary I did not hit.
- The constructive reframe (heterogeneous adversarial review + deterministic verification) is my synthesis, not a result anyone has benchmarked.

**Unresolved / could not verify:**
- Exact numbers from "The Cost of Consensus" (2605.00914) and "Minority Sentinel" (2606.29270) — PDFs returned metadata only. Titles and directional findings are recorded; treat magnitudes as unknown.
- I could not inspect thebus itself; it is not present in this repo (grep for governance/dissent/membership/vote returns only two incidental hits in AGENTS.md and START-HERE.md). All criticism of thebus is against the *description* given in the brief. If the implementation is already a verification substrate rather than an org chart, several objections weaken.
- Several sources are 2026-dated arXiv preprints, some read via search summarisation rather than full text. Preprints, not peer-reviewed.

---

## Surprises

1. **The two failure modes governance targets are literally the smallest two of fourteen.** I expected governance to rank low. I did not expect 0.85% and 1.9% — dead last and third-from-last. That is not "an underrated area"; that is noise.

2. **Anthropic, the most pro-multi-agent source available, disqualifies this exact use case in its own post.** The 90.2% number is universally quoted and the exclusions in the same document — coding, shared context, many dependencies — almost never are. The single strongest citation *for* multi-agent is a citation *against* this application.

3. **"Token usage by itself explains 80% of the variance."** Anthropic's own framing implies most of the multi-agent gain is bought compute, not architecture. That reframes the entire 15× question: you may be able to buy the same gain by giving one agent more thinking budget, with no coordination tax.

4. **LLM judges are near-random at catching agent lies (AUROC 0.54 on coding agents) while TF-IDF gets 0.95.** Any governance design that has agents adjudicate other agents' status claims is building its foundation on a coin flip. This is the most actionable single fact in the report.

5. **Single-agent consumed nearly 2× the tokens of multi-agent in at least one study (121K vs 63K).** The "multi-agent is always more expensive" framing is not universally true — multi-agent can be *cheaper* by stopping earlier. Which, given the premature-termination and false-success findings, may be a bug reported as a feature. Worth flagging as a genuine complication to the cost argument rather than hiding it.

6. **The corpus already ran this experiment and wrote down the answer.** The most decisive evidence against the hypothesis is not in the literature; it is in `workflow/canon/DECISIONS.md`, dated ten days ago, with a named reopen condition that has not been met.

---

## Assumption candidates

Proposed for the Assumption Registry, in the repo's format:

- **Assumption:** The binding constraint on multi-harness output is verified state, not coordination. Governance-shaped failure modes are ≤12% of observed failures; specification + verification + termination are ~77%.
  **Source:** MAST (arXiv 2503.13657) mode distribution; false-success prevalence (arXiv 2606.09863).
  **Status:** unverified in this corpus — no local measurement of failure-mode distribution exists.
  **Affects:** whether thebus is built at all; what P4 measures.

- **Assumption:** Agent-reported status is the least trustworthy field in any fleet record, and LLM adjudication of it is near-random. Deterministic checkers must gate every "done".
  **Source:** false-success 45–76%; judge AUROC 0.54–0.65 vs TF-IDF 0.83–0.95 (arXiv 2606.09863).
  **Status:** consistent with existing local practice (sabotage_test / stress_test) but never stated as a law.
  **Affects:** LAWS.md; receipt schema; any thebus verification design.

- **Assumption:** Cross-vendor heterogeneity, not agent count, is the only mechanism with evidence of producing multi-agent gains (>30% error reduction cross-family vs "little" same-family).
  **Source:** arXiv 2510.20963; arXiv 2502.08788.
  **Status:** unverified locally; the 30-day campaign did not isolate heterogeneity from concurrency.
  **Affects:** P3 ablation design — the ablation should test *heterogeneous review of one artifact*, not *concurrent fleet*, because the concurrency arm has already lost once.

- **Assumption:** Damping pessimistic agent reports is contraindicated; the documented pathology is over-claimed success, so dissenting failure reports are the scarce high-value signal and must be preserved without discount.
  **Source:** arXiv 2606.09863 (false success); conformity literature (arXiv 2509.05396, 2604.02668).
  **Status:** unverified — "despair contagion" has no located literature; absence of evidence, searched several ways.
  **Affects:** thebus dissent semantics; any watcher/babysitter design.

- **Assumption:** Governance primitives that terminate in human decisions (voting, escalation) increase load on the resource whose starvation is the corpus's #1 project-death mode.
  **Source:** 2026-08-08 audit (two earlier private projects both died at "pending the operator"); GATES.md 48h SLA.
  **Status:** inferred, unmeasured.
  **Affects:** GATES.md; whether escalation is added at all.

**Recommended decision-row language, if this is accepted:**

> | 2026-08-18 | Build a cross-harness governance layer (thebus)? | No — reframe as a verification substrate; keep heterogeneous adversarial review, drop membership/seats/voting | Governance-shaped modes are ~2.75% of MAST failures vs ~77% for spec/verification/termination; Anthropic excludes shared-context and coding domains; single-agent wins at matched compute; the corpus's own 30-day campaign returned zero confirmed improvements (its cost being a metering figure the owning project later marked unverified and withdrew) | The P3 ablation shows a *heterogeneous* fleet beating one strong agent on a real interdependent task, at matched token spend |

---

## Sources

**Multi-agent failure taxonomies**
- Cemri, Pan, Yang et al., "Why Do Multi-Agent LLM Systems Fail?" — https://arxiv.org/abs/2503.13657 (full text: https://arxiv.org/html/2503.13657 ; PDF: https://arxiv.org/pdf/2503.13657)
- Secondary summary of MAST — https://thegrigorian.medium.com/why-do-multi-agent-llm-systems-fail-14dc34e0f3cb
- "Context Is the Bottleneck: Why Multi-Agent LLM Systems Fail, and What MAST Teaches Us" — https://medium.com/@daniel.lh.gordon/context-is-the-bottleneck-why-multi-agent-llm-systems-fail-and-what-mast-teaches-us-b336b9f76e03

**The single-agent case**
- Walden Yan / Cognition, "Don't Build Multi-Agents" — https://cognition.com/blog/dont-build-multi-agents
- "AI Leaders Clash Over Agent Architecture as Cognition and Anthropic Reveal Opposing Design Strategies" — https://www.ctol.digital/news/ai-leaders-clash-agent-architecture-cognition-anthropic-strategies/
- "Soloists to Ensembles: the evolving debate between single-agent and multi-agent systems" — https://www.piyush.cc/p/soloists-to-ensembles-the-evolving

**Compute-matched benchmarks (single ≥ multi)**
- "Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets" — https://arxiv.org/html/2604.02460v1
- "When and Why Does Multi-Agent Debate Fail and Does It Really Underperform?" — https://arxiv.org/html/2510.20963v2
- "Stop Overvaluing Multi-Agent Debate — We Must Rethink Evaluation and Embrace Model Heterogeneity" — https://arxiv.org/abs/2502.08788
- "Multi-LLM-Agents Debate — Performance, Efficiency, and Scaling Challenges" (ICLR Blogposts 2025) — https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/
- "Multi-agent AI keeps collapsing back into one agent. A fair test just proved it." — https://learnagentic.substack.com/p/multi-agent-ai-keeps-collapsing-back

**Conformity, sycophancy, dissent suppression**
- "Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate" (ICML MAS Workshop 2025) — https://arxiv.org/abs/2509.05396 (PDF: https://arxiv.org/pdf/2509.05396)
- "Too Polite to Disagree: Understanding Sycophancy Propagation in Multi-Agent Systems" — https://arxiv.org/html/2604.02668v2
- "The Cost of Consensus: Isolated Self-Correction Prevails Over Unguided Homogeneous Multi-Agent Debate" — https://arxiv.org/pdf/2605.00914
- "Minority Sentinel: When to Overturn Majority Voting in Multi-Agent LLM Debates" — https://arxiv.org/pdf/2606.29270
- "Peacemaker or Troublemaker: How Sycophancy Shapes Multi-Agent Debate" — https://arxiv.org/pdf/2509.23055
- "Most LLM Conformity Needs No Speaker: Measuring the Speaker-Free Floor in Peer-Pressure Benchmarks" — https://arxiv.org/pdf/2607.05545
- "Conformity Mitigations in Large Language Models Lie on a Single Resistance–Receptivity Frontier" — https://arxiv.org/html/2608.11247
- "Persona Inconstancy in Multi-Agent LLM Collaboration: Conformity, Confabulation, and Impersonation" — https://arxiv.org/pdf/2405.03862

**Over-claiming success (the actual documented pathology)**
- "From Confident Closing to Silent Failure: Characterizing False Success in LLM Agents" — https://arxiv.org/abs/2606.09863 (full text: https://arxiv.org/html/2606.09863)
- "Beyond Task Completion: Revealing Corrupt Success in LLM Agents through Procedure-Aware Evaluation" — https://arxiv.org/html/2603.03116
- "LLM Agents Assert Success While Tasks Fail Silently" — https://www.bymachine.news/llm-agents-false-success-silent-failures
- "Do Agents Know What They Can't Do? Evaluating Feasibility Awareness in Tool-Using Agents" — https://arxiv.org/pdf/2605.28532

**Contagion / early abort (searched for "despair contagion"; these are the nearest hits)**
- "Reliability–Contagion Feasibility in LLM Multi-Agent Networks" — https://arxiv.org/html/2607.21912v1
- "How Affect Propagates among LLM Agents: Emergent Emotional Contagion in Crowd Simulation" — https://arxiv.org/html/2607.25140v1
- "Doomed from the Start: Early Abort of LLM Agent Episodes via a Recall-Controlled Probe Cascade" — https://arxiv.org/html/2607.06503v1
- "Contagion Networks: Evaluator Preference Propagation in Multi-Agent LLM Systems" — https://arxiv.org/pdf/2606.20493
- "Delayed Verification Destabilizes Multi-Agent LLM Belief" — https://arxiv.org/html/2606.27409

**Cost**
- Anthropic, "How we built our multi-agent research system" — https://www.anthropic.com/engineering/multi-agent-research-system
- "Multi-agent AI costs 15x more, and almost nobody routes it" — https://getnadir.com/blog/multi-agent-orchestration-15x-token-cost/
- "Multi-Agent Cost Compounding: Why 3 Agents Cost 10x" — https://www.augmentcode.com/guides/multi-agent-cost-compounding
- "AI Agents Burn 50x More Tokens Than Chats" (cites Gartner Mar 2026, 5–30×) — https://leanopstech.com/blog/agentic-ai-cost-runaway-token-budget-2026/
- "AI Agent Cost Optimization: Token Economics and FinOps in Production" — https://zylos.ai/research/2026-02-19-ai-agent-cost-optimization-token-economics/
- ZenML LLMOps case study of Anthropic's system — https://www.zenml.io/llmops-database/building-production-multi-agent-research-systems-with-claude

**Simpler alternatives (context management for one strong agent)**
- Anthropic, "Effective context engineering for AI agents" — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- "Context Engineering: Agent Reliability Playbook 2026" (reports context editing +29%, with memory tool +39%, 84% token reduction on 100-turn eval) — https://www.digitalapplied.com/blog/context-engineering-agent-reliability-playbook-2026
- "ACON: Optimizing Context Compression for Long-horizon LLM Agents" — https://arxiv.org/pdf/2510.00615
- "Slipstream: Trajectory-Grounded Compaction Validation for Long-Horizon Agents" — https://arxiv.org/pdf/2605.08580
- "Diagnosing and Mitigating Context Rot in Long-horizon Search" — https://arxiv.org/pdf/2606.29718

**The operator's own corpus (primary; files in the sibling repository — publication pending, not linked here)**
- `workflow/canon/DECISIONS.md` — 2026-08-08 fleet-vs-single row; Law 9 / spend row (a metering figure the owning project later marked unverified and withdrew)
- `workflow/handoffs/2026-08-08-p1-complete.md` — WHAT NOT TO DO: "Do not bolt fleet infrastructure (buses, seats, watchers) onto [the project] preemptively"
- `workflow/PLAN.md` — Assumption Registry: one strong agent vs fleet, status holding
- Corpus audit artifact referenced in the handoff (a private working document; not reproduced here)
