# Phase 1 research — cross-family reviewer experiment

Date: 2026-08-18
Scope: four questions only, in service of one experiment's design. Nothing beyond.

Experiment under design: four compute-matched arms reviewing the same completed-task artifacts —
(a) same-session self-check, (b) fresh reviewer, same model, same harness, (c) same harness, different
model family, (d) different harness AND different family. Primary comparison: (c) vs (b).

---

## Q1 mutation design

### 1.1 Is claim-preserving mutation sound?

**Yes in principle, with one correction to the ground-truth argument and one serious external-validity
warning.**

The underlying assumption is mutation testing's *coupling effect*: simple syntactic faults are coupled
to the complex real faults you actually care about. This is the best-supported assumption in the area.
Petrović, Ivanković, Fraser & Just analysed almost 15 million mutants at Google and found evidence that
"mutants are indeed coupled with real faults," and that mutants introduced at bug-introducing changes
could have caught the bug pre-release (<https://arxiv.org/abs/2103.07189>). The canonical prior result
is Just et al., "Are mutants a valid substitute for real faults?" FSE 2014
(<https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf>) — I could not extract
its numbers this session (PDF decode failed, Semantic Scholar rate-limited), so treat its specific
percentages as *unverified* here; the direction of the finding is corroborated by the Google work above.

**Correction to your framing.** You do not actually need "the mutant is non-equivalent." You need the
stronger and *different* condition: **the mutant falsifies a proposition the completion claim asserts.**
Two distinct poisons, not one:

1. **Equivalent mutants** — no behavioural change, claim stays true. You already identified this.
2. **Non-equivalent but claim-irrelevant mutants** — real behaviour change, but the receipt's claim is
   still substantively true. Mutate a logging call, a metrics counter, or a debug branch, and "implemented
   the X endpoint" remains true. This is Google's *arid mutant* problem wearing a new hat, and in practice
   it is **the larger of the two risks**, because arid mutants are far more common than equivalent ones.

Google's definition, which you should adopt verbatim as your exclusion criterion: an unproductive mutant
"is either trivially equivalent to the original program or it is detectable, but adding a test for it
would not improve the test suite" (<https://arxiv.org/abs/2102.11378>). Substitute "would not make the
completion claim false" for "would not improve the test suite."

### 1.2 The operational fix — a kill-test certificate (recommended, do this)

You can eliminate the equivalent-mutant problem entirely and automatically, without adjudication, by
**inverting the usual mutation-testing selection rule**:

1. Start from a real completed task whose commit has a passing test suite / acceptance command.
2. Apply the mutation.
3. Run the repo's own tests. **Keep only mutants that are KILLED.** Discard survivors.
4. Withhold the test result from the reviewer; hand them the code plus the verbatim completion claim.

A killed mutant is, by construction, provably non-equivalent *and* observable through the project's own
oracle — which is exactly the oracle the completion claim implicitly appeals to. Ground truth is a
by-product of the build, not a human judgement call. Surviving mutants are ambiguous (equivalent, or a
genuine test-suite gap) and should simply be dropped; in normal mutation testing survivors are the
interesting ones, here they are the discards.

**Cost of this trick, stated honestly:** it restricts your eval to defects with a clean automated oracle.
A large share of genuine agent false-success in the wild has *no* test — the claim is about something
untested. So the kill-test stratum is a lower bound on difficulty and a biased sample of defect types.
Mitigate with a second, smaller, hand-adjudicated stratum (§1.5).

### 1.3 Operator taxonomy

**Tier A — use these.** Semantically real, invisible to a linter/type checker, plausibly missed by a
careless reviewer. Anchored on the five operators Google actually runs in production, with their measured
developer-rated productivity (<https://arxiv.org/abs/2102.11378>):

| Operator | Example | Productivity at Google | Why it qualifies |
|---|---|---|---|
| **ROR** — relational operator replacement | `<` → `<=`, `>` → `>=` | **84.1%** (highest) | Classic off-by-one/boundary. Type-safe, lint-clean, real. |
| **LCR** — logical connector replacement | `and` → `or` | ~ROR | Type-safe; changes semantics; near-invisible on skim. |
| **SBR** — statement/block removal | drop a guard, drop a side effect | ~ROR | High variance — see caution below. |
| **AOR** — arithmetic operator replacement | `+` → `-`, `*` → `/` | ~79% | Type-safe when operand types match. |
| **UOI** — unary operator insertion | insert/remove `not`, negation | **74.5%** (lowest) | Weakest of the five; keep but downweight. |

Plus two operators PIT classifies as experimental but which are *ideal* for your purpose because a type
checker structurally cannot see them (<https://pitest.org/quickstart/mutators/>):

- **Argument swap / argument propagation** — swap two same-typed arguments at a call site. Undetectable by
  any type checker, highly plausible as a real slip, and semantically real.
- **Conditionals boundary** — PIT's default `<`↔`<=` family; this overlaps ROR and is PIT-default precisely
  because it is stable and rarely equivalent.

Caution on **SBR**: MuRS (<https://arxiv.org/abs/2306.09130>) reports that statement-deletion mutants drew
*both the most positive and the most negative* developer feedback at Google — highest signal and highest
noise. Keep SBR, but gate it hardest with the kill-test filter.

**Tier B — do not use.** PIT's own documentation names these as equivalent-mutant factories:

- **Remove Conditionals** (replace a condition with `true`/`false`) — heavy overlap, frequently equivalent.
- **Inline Constant** — "likely to create equivalent mutations," especially when the constant equals a type
  default. *Exception:* perturbing a **semantically meaningful** constant (a timeout, a retry count, a page
  limit, a threshold) is Tier A — it is the arbitrary-literal case that is poison.
- **Constructor Calls → null** — "fairly unstable."
- **Non-Void Method Calls → default value** — "may also create equivalent mutations."
- **Member Variable removal** — "likely to create equivalent mutations."
- **Void Method Call removal** — PIT-default, but for you it is the canonical *arid* case (removing a
  logging/metrics call is non-equivalent yet claim-irrelevant). Exclude.
- **Increments** (`i++` → `i--`) on loop counters unused after the loop — commonly equivalent.

**Tier C — excluded by definition (your linter already gets these 17/17).** Renames, import deletions,
arity changes, return-type changes, and your existing document/schema defects. Nothing here tests review.

**Tier A+ — the highest-fidelity source, and better than synthetic mutation: reverse the fix.** Beller et
al.'s Facebook study did not use textbook operators; they "semi-automatically learn error-inducing patterns
from a corpus of common Java coding errors and from changes that caused operational anomalies at Facebook"
(<https://arxiv.org/abs/2010.13464>). More than half the resulting mutants survived Facebook's full test
suite, and ~half of 26 developers would act on the mutant shown to them. **You have the same resource**:
your repo's own bug-fix commit history. Inverting a real fix gives a defect drawn from the true defect
distribution rather than an operator grammar. This should be your realism stratum.

### 1.4 How practitioners handle equivalent mutants

Nobody solves it (it is undecidable in general); five mitigations, in descending order of relevance to you:

1. **Dynamic kill-filter** — the certificate in §1.2. Cheapest, strongest, fully automatic. *Use this.*
2. **Suppress unproductive mutants rather than prove equivalence (Google's answer).** Impact is dramatic:
   median **820** mutants per changelist under naive mutagenesis → **77** with one-mutant-per-line → **7**
   with arid-node suppression, a two-orders-of-magnitude cut. Developers initially rated **85%** of surfaced
   mutants unproductive; after suppression, **82%** were rated productive, improving from 80% to 89% over
   time. Reported mutants are capped at 7× the number of files in the changelist
   (<https://arxiv.org/abs/2102.11378>). MuRS learns suppression rules from historical feedback and cut the
   negative-feedback ratio to 11.45% vs 12.41% baseline in an A/B test
   (<https://arxiv.org/abs/2306.09130>).
3. **Trivial Compiler Equivalence (TCE)** — compile mutant and original with optimisation, compare binaries;
   identical means equivalent. Papadakis et al., ICSE 2015. *Not on arXiv; I could not verify a URL this
   session — treat as a pointer, not a citation.* Largely inapplicable to Python anyway.
4. **Prevalence is lower than feared.** Straubinger, Degenhart & Fraser found "less than 10% of manually
   created mutants are equivalent," but that humans are bad at identifying which
   (<https://arxiv.org/abs/2404.09241>). So do not rely on human adjudication.
5. **LLM-based equivalent-mutant detection** — a production agent at Meta reports **0.79 precision / 0.47
   recall** (<https://arxiv.org/abs/2501.12862>); a research study reports a 35.69% F1 improvement over
   traditional techniques (<https://arxiv.org/abs/2408.01760>). Recall of 0.47 is far too low to be your
   ground-truth gate. Use as a triage filter at most.

### 1.5 Is there a better-known technique, or a corpus you can reuse instead of building?

**Check these three before you build anything.** At least one may be a drop-in.

- **Terminal Wrench** — Zhong et al., "Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops"
  (<https://arxiv.org/abs/2606.08960>, 2026-06-08). Audited 1,968 tasks across five terminal-agent
  benchmarks; **323 (16%) are vulnerable to reward hacking by frontier models**; released **323 hackable
  environments and 3,632 hack trajectories** with exploits and patched verifiers as ground truth. This is
  *literally a false-success corpus with ground truth* — an agent passed without doing the work. **Closest
  existing thing to what you want; evaluate it first.** (No direct dataset URL stated in the abstract; the
  authors say they release it.)
- **HackDetect** — Shao et al., "Do Agent Benchmarks Measure Capability? Protocol Validity in the Age of
  Agentic AI" (<https://arxiv.org/abs/2607.22368>, 2026-07-24). Audited **2,385 traces across 15 agent
  benchmarks**; problematic patterns in **67% of Frontier Science traces and 66.7% of AutoLab tasks**, with
  score inflation of 0.45–1.00. Public dataset release not stated in the abstract — worth an email.
- **SWE-Marathon** (<https://arxiv.org/abs/2606.07682>, 2026-06-05) — 20 ultra-long-horizon tasks with
  **13.8% reward-hacking behaviour** documented. Small, but the tasks are the right shape.

Adjacent / synthesis sources rather than reusable corpora:
- **MegaBugFix** (<https://arxiv.org/abs/2606.29088>) — 12,629 buggy Python programs synthesised from
  correct ones via LLM-generated diff-based corruption. A ready-made supply of semantic defects; it has no
  completion claims attached, so you would still author those.
- **SWE-Bench ProMax** (<https://arxiv.org/abs/2608.09802>) — cites an audit finding "nearly 60% of unsolved
  SWE-bench Verified instances contain flawed tests." Read as a *warning about oracle quality*, not a source.

### 1.6 The finding that most threatens this experiment

Kumar, Bararia & Raj, "Bigger Isn't Always Better: A Comparative Evaluation of LLMs for Automated Code
Review" (<https://arxiv.org/abs/2606.15689>, 2026-04-09) evaluated five models (Claude Sonnet 4.6, Claude
Haiku 4.5, GPT-5.4 mini, Minimax M2.7, GLM-5 Turbo) on 150 samples: **100 synthetic mutation-injected bugs
and 50 real bug-fix PRs**. Result:

> best model F1 = **0.847** on the synthetic mutation-injected samples, F1 = **0.066** on the real PRs — a
> **92% degradation**. "Synthetic-only evaluation dramatically overestimates model capability."

Two consequences for you, both structural:

1. **Ceiling effect kills your power.** Your assumed baseline detection rate of 0.4–0.6 is very likely wrong
   for synthetic mutants; expect ~0.8+. At p_b = 0.85 there is only 0.15 of headroom and the (c)−(b) gap
   compresses toward zero. Every n in §Q2 assumes a mid-range baseline; if you land at 0.85 the required n
   rises sharply and a null becomes uninterpretable.
2. **External validity.** An effect measured on mutants may simply not transfer to real false-success.

*Mitigations:* pilot to measure the actual baseline before committing n; tune operator difficulty (or
mutate deeper in the call graph, or into less-reviewed files) to land p_b near 0.5; and run the
reverse-the-fix stratum (§1.3) in parallel, pre-registering that you report both strata separately and
never pool them.

---

## Q2 power

All numbers below: α = 0.05 two-sided, power = 0.80. Computed directly (script:
`scratchpad/power.py`), not taken from a table.

### 2.1 Which test

**Use McNemar, because you can pair — and you should pair.** Every arm reviews the same artifacts, so the
outcome is a paired binary (detected / not detected) per item. The independent two-proportion z-test throws
away the item-level pairing and is strictly wasteful here.

Specifics:
- Use **McNemar's exact (or mid-p) test**, not the asymptotic χ². Your discordant-pair counts land in the
  10–70 range (table below) and the asymptotic approximation is unreliable there. Mid-p is the better
  default: exact McNemar is conservative, mid-p is closer to nominal α.
- For the full four-arm model, fit a **mixed-effects logistic regression** — `detected ~ arm + (1 | item)`
  — as the pre-registered analysis, with McNemar as the simple, reportable primary. Add `(1 | operator_type)`
  and `(1 | source_repo)` if you stratify. This handles the four arms in one model, respects the nesting,
  and lets you add the difficulty covariates you will inevitably want.
- Fisher's exact is the right choice only if you end up **unpaired** with small n. You are not unpaired.

### 2.2 Unpaired two-proportion z, n **per arm**

Included for reference / as the "if we cannot pair" fallback. CC = Casagrande–Pike–Smith continuity
correction (the honest number if you will use Fisher or a corrected z).

| baseline p_b | Δ | p_c | n/arm | n/arm with CC |
|---|---|---|---|---|
| 0.40 | 0.15 | 0.55 | **173** | 186 |
| 0.40 | 0.20 | 0.60 | **97** | 107 |
| 0.40 | 0.30 | 0.70 | **42** | 49 |
| 0.50 | 0.15 | 0.65 | **170** | 183 |
| 0.50 | 0.20 | 0.70 | **93** | 103 |
| 0.50 | 0.30 | 0.80 | **39** | 45 |
| 0.60 | 0.15 | 0.75 | **152** | 165 |
| 0.60 | 0.20 | 0.80 | **82** | 91 |
| 0.60 | 0.30 | 0.90 | **32** | 38 |

Headline: **~170 per arm for 15 pp, ~95 for 20 pp, ~40 for 30 pp**, essentially flat across baselines in
0.4–0.6.

### 2.3 Paired McNemar, n **items** (each item seen by every arm)

Paired n depends on Δ *and* on the **discordance rate ψ = P(b right, c wrong) + P(b wrong, c right)**. ψ is
the whole story and you cannot know it without a pilot. Δ ≤ ψ always.

| Δ | ψ | n items | of which discordant |
|---|---|---|---|
| 0.15 | 0.20 | **68** | 14 |
| 0.15 | 0.25 | **85** | 22 |
| 0.15 | 0.35 | **120** | 42 |
| 0.15 | 0.45 | **155** | 70 |
| 0.20 | 0.25 | **47** | 12 |
| 0.20 | 0.30 | **57** | 17 |
| 0.20 | 0.40 | **77** | 31 |
| 0.20 | 0.50 | **96** | 48 |
| 0.30 | 0.35 | **29** | 10 |
| 0.30 | 0.40 | **33** | 13 |
| 0.30 | 0.50 | **42** | 21 |
| 0.30 | 0.60 | **50** | 30 |

### 2.4 Does pairing change n, and by how much?

**Yes, and be precise about which cost it reduces.**

| Δ | ψ | unpaired: n/arm (× 2 arms = item-reviews) | paired: n items | distinct artifacts saved |
|---|---|---|---|---|
| 0.15 | 0.20 | 170 (340) | **68** | 272 |
| 0.15 | 0.35 | 170 (340) | **120** | 220 |
| 0.20 | 0.30 | 93 (186) | **57** | 129 |
| 0.20 | 0.50 | 93 (186) | **96** | 90 |
| 0.30 | 0.40 | 39 (78) | **33** | 45 |
| 0.30 | 0.60 | 39 (78) | **50** | 28 |

Reading this correctly:
- Pairing's saving is on **artifact construction** — the expensive, human-gated part of your pipeline. At
  Δ=0.15, ψ=0.20 you build 68 artifacts instead of 340. That is a 5× reduction in the bottleneck.
- Pairing does **not** proportionally reduce total review calls: 68 items × 4 arms = 272 reviews vs 340 in
  the unpaired 2-arm design. You save artifacts, not compute. Given your compute-matching constraint this
  is the right trade.
- **The gain scales with how correlated the arms are.** Low ψ (arms usually agree) → pairing wins big. High
  ψ (arms nearly independent) → the gain shrinks and can invert. **Q4 predicts ψ will be LOW**, because
  model errors across families are strongly correlated. So pairing is very likely a large win here — and if
  it is not, that itself is your most interesting result.

### 2.5 Multiple arms without inflating false positives

**Recommended (no cost in n):** pre-register **(c) vs (b) as the single primary endpoint** tested at
α = 0.05. Report (a) and (d) as secondary/exploratory with confidence intervals and *no inferential claim*.
This is standard clinical-trial practice, it is the cheapest option, and it is honest as long as it is
written down before you look at the data. Your existing preregistration habit already supports this.

**If you want family-wise control** across the three vs-(b) contrasts:
- **Dunnett's test** is the correct instrument — it is designed exactly for many-treatments-vs-one-control
  and is uniformly less conservative than Bonferroni. Use (b) as the control.
- **Holm–Bonferroni** is the simplest correct alternative: same FWER as Bonferroni, uniformly more powerful,
  no assumptions. Fine as a fallback.
- **Bonferroni** costs real n. At α = 0.05/3 = 0.0167:

| Δ | unpaired n/arm (0.5 baseline) | paired n items (ψ = Δ+0.20) |
|---|---|---|
| 0.15 | 227 (from 170) | 161 (from 120) |
| 0.20 | 125 (from 93) | 102 (from 77) |
| 0.30 | 52 (from 39) | 56 (from 42) |

So Bonferroni costs roughly **+33% n**. Dunnett or Holm recovers most of that. Single-primary-endpoint
costs nothing.

**Do not** run all 6 pairwise comparisons and correct for 6 — you only care about 3 contrasts against (b),
and really about 1.

### 2.6 Practical planning recommendation

Run a **~30-item pilot** first. You need two numbers you currently do not have and cannot guess: the
baseline detection rate p_b (§1.6 says your 0.4–0.6 assumption is probably wrong) and the discordance rate
ψ (which drives paired n entirely). Then commit n. Budget for **60–120 items** as the realistic range if
you target Δ = 0.20 with a single primary endpoint.

Also, since arms share items: randomise arm order, and for arm (a) — same-session self-check — note it is
not exchangeable with the others (it sees the generation context), so it is a different construct, not just
a different reviewer. Keep it clearly labelled as such.

---

## Q3 lead verification

### (a) Community Notes bridging — **CONFIRMED, and reusable with caveats**

- The scoring model is matrix factorization with a per-note intercept. Exact predicted rating:
  **r̂ᵤₙ = μ + iᵤ + iₙ + fᵤ·fₙ** (global intercept, rater intercept, **note intercept**, plus dot product of
  rater/note latent factor vectors). The **note intercept iₙ IS the public helpfulness score**.
  <https://github.com/twitter/communitynotes/blob/main/documentation/under-the-hood/ranking-notes.md>
  (rendered: <https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes>)
- Loss: Σ(rᵤₙ − r̂ᵤₙ)² + λᵢ(iᵤ² + iₙ² + μ²) + λf(‖fᵤ‖² + ‖fₙ‖²), with **λᵢ = 0.15, λf = 0.03**. The
  intercept regularization is deliberately 5× the factor regularization — that asymmetry is the entire
  "common ground" mechanism: it forces a note to be rated helpful by raters at *different* factor positions
  before iₙ can rise. "Helpful" threshold: **iₙ ≥ 0.40 and |fₙ| < 0.50**.
- **Open source: yes.** <https://github.com/twitter/communitynotes> (live; URL unchanged post-rebrand).
  Python 3.10, **Apache-2.0**. Scoring code in `scoring/src/scoring` (`matrix_factorization/`,
  `mf_core_scorer.py`, `mf_base_scorer.py`, `mf_group_scorer.py`, `helpfulness_scores.py`).
- **Reusability: partial.** It runs (`python main.py` in `scoring/src`) but is **not a packaged library** —
  no `setup.py`/`pyproject.toml`, only `requirements.txt` + `src`. It is a periodic export of an internal
  production pipeline, and the README says X will not accept API-altering PRs to `scoring/src`. Treat it as
  reference code to port ~200 lines from, not as a dependency.
- **No pip-installable third-party alternative found.** The only related implementation located is
  `social-protocols/bridge-based-ranking` — **in Julia**, 6 stars, explicitly experimental, tied to
  <https://jonathanwarden.com/understanding-bridge-based-ranking>. PyPI name probes for `birdwatch`,
  `community-notes`, `bridging-algorithm`, `bridging-based-ranking`, `pol-is`, `pluralistic-ai` all 404.
  (PyPI full-text search was bot-blocked, so this is not exhaustive.)

### (b) "Gaming Consensus" arXiv 2607.01824 — **CONFIRMED, numbers match**

- <https://arxiv.org/abs/2607.01824> resolves. **"Gaming Consensus: Coordinated Manipulation in Crowdsourced
  Fact-Checking."** Selvam, Baxter, Hilgard, Miller, Coleman, Vitercik, Koyejo. Submitted **2026-07-02**.
  Note the author list includes X's own Community Notes leads (Baxter, Coleman) — this is a
  first-party-adjacent red-team paper, which raises its credibility.
- **Cost: ≈$30.50/note**, from the paper's own worked calculation (C ≈ 0 + 10×1×3 + 10×0.05 = $30.50, with
  account maintenance the dominant ~$30 term). Your "~$30" is right.
- **10.7% figure: confirmed near-verbatim** — "up to 10.7% of lower quality notes could be manipulated above
  consensus thresholds using less than 10 ratings" (when rater factors span [−1, 1]).
- Bonus finding worth knowing: the paper reports a counterintuitive flaw where **marking notes "Not Helpful"
  paradoxically increases their helpfulness scores**. Mitigations have since been deployed by X.

**Does it generalise to a design that REQUIRES diversity? — Your worry is correct, with one important
qualification.** The attack mechanism is exactly the thing you feared: sybil accounts **first establish
diverse positions in latent factor space, then coordinate** to boost a target note. The adversary
manufactures the diversity signal itself. The paper's own framing is that the diversity/bridging requirement
does **not** stop this; what mitigates it is *additional* machinery layered on top — notably population-sample
filtering using randomly-notified, non-self-selected raters (also documented in X's safeguards docs).
So: **"if you require diversity, an adversary supplies diversity" is supported.**

**But the qualification matters more than the confirmation for your experiment.** The paper is about
adversarial human sybils in an open-enrolment system. Your reviewer pool is *closed and chosen by you* —
there is no adversary supplying fake reviewers. The transferable lesson is therefore **not** "diversity
requirements are gameable"; it is the deeper one: **the thing that carries the bridging property is the
latent factor position, not the label.** A diversity requirement stated over labels (here: model-family
names) is satisfiable by entities that are identical in latent space. That is the same finding Q4 reaches
from a completely different direction, and it is the single most load-bearing point in this document.

Scope note: this lead, and (a) and (c), are about **aggregating many raters into a quorum**. Your four-arm
experiment has **one reviewer per arm**. These leads are relevant to a *later* quorum design, not to the
experiment you are currently specifying. Do not let them expand its scope.

### (c) RCT arXiv 2603.19626 — **CONFIRMED, with a correction you should carry**

- <https://arxiv.org/abs/2603.19626> resolves. **"The Prosocial Ranking Challenge: Reducing Polarization on
  Social Media without Sacrificing Engagement."** Jonathan Stray et al. (~40+ co-authors incl. Budak, Bail,
  Bernstein, Tucker, Willer, Wojcieszak). Submitted **2026-03-20**.
- **N = 9,386 confirmed.** Browser-extension field study modifying rankings across Facebook, Reddit and
  X/Twitter over ~6 months around the 2024 US presidential election.
- Six arms: control plus five ranking treatments, one named literally **"Uprank Bridging."** Others:
  "Uprank Bridging + Downrank Toxic," "Challenging Stereotypes," "Diverse Approval," "Add News."
- **Bridging-alone finding confirmed:** the "Uprank Bridging" arm produced **no statistically significant
  reduction in polarization.**
- **Correction to how you are holding it:** other arms *did* reach significance — **"Uprank Bridging +
  Downrank Toxic" (~0.042 SD, p<0.05)** and **"Add News" (~0.044 SD, p<0.05)** — and the **pooled effect
  across all arms was ~0.027 SD (p<0.05)**, about a 1.5-point shift on a 100-point feeling thermometer. So
  the accurate statement is "bridging *alone* was null; bridging *combined with* toxicity-downranking was
  significant but small," not "the study found bridging doesn't work."
- Per-arm sample sizes (1,312 / 1,400 / 1,391 / 1,433 / 1,444 / 2,729) came via an AI-summarised HTML read
  and do not cleanly sum to 9,386 — treat the per-arm breakdown as **approximate**. Headline N, six-arm
  design, the bridging-alone null, and the two significant arms are higher-confidence.

**Design implication:** a bridging-style mechanism as a *sole* intervention has one high-quality RCT showing
a null. If you later build a bridging quorum, expect it to need a second component to do anything.

---

## Q4 is family the right axis

**Short answer: no — not as stated. "Different model family" is a weak proxy for the thing you actually
want, and the empirical record is unusually one-sided against it. This undercuts the experiment's premise
and is the most important finding in this document.**

### 4.1 Evidence that families are MORE correlated than assumed

1. **Kim, Garg, Peng, Garg, "Correlated Errors in Large Language Models"** (ICML 2025),
   <https://arxiv.org/abs/2506.07962>. N = 350+ LLMs across two leaderboards plus a real resume-screening
   task. **On one leaderboard, models agree 60% of the time when both err.** They explicitly tested and
   **rejected** the "different provider/architecture ⇒ independent" hypothesis: "larger and more accurate
   models have highly correlated errors, even with distinct architectures and providers." **Capability level
   predicts error correlation better than family origin does.** This is a direct, large-scale, peer-reviewed
   refutation of your independence axis.
2. **Goel, Struber, Auzina, Chandra, Kumaraguru, Kiela, Prabhu, Bethge, Geiping, "Great Models Think Alike
   and this Undermines AI Oversight,"** <https://arxiv.org/abs/2502.04313> (verified). Introduces **CAPA**
   (Chance-Adjusted Probabilistic Agreement, κₚ) — mistake overlap corrected for chance given each model's
   accuracy. ~39 models across Qwen2.5 / Llama-3.1-3.3 / Gemma-2 / Ministral, plus a 130-model leaderboard
   analysis. **Mistake similarity κₚ rises with capability**, regardless of family — the trend is getting
   *worse* as models improve. Also: **LLM-judge affinity bias r ≈ 0.84 (p<0.01)** between judgment score and
   CAPA across 9 judges; partial correlations controlling for target accuracy **r = 0.35–0.65**. Concrete
   instance: Qwen2.5-72B-as-judge rated its own family's 7B model higher (71%) than a *more capable*
   different-family Llama-3.1-70B (67%).
3. **Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations,"**
   <https://arxiv.org/abs/2404.13076>. GPT-4 self-preference **0.912** on CNN/DailyMail, **0.705** on XSUM
   (0.5 = unbiased). Self-recognition→self-preference **Kendall's τ up to 0.82**. The critical detail for
   you: **Llama-2 showed near-zero bias only because it "is completely incapable of distinguishing itself
   from GPT-3.5 and GPT-4"** — i.e. cross-family judging looks clean when the judge is too weak to notice,
   not because cross-family is structurally sound. As judges get stronger, family recognition gets *easier*.
4. **Rosales & Miret, "Diverse LLMs or Diverse Question Interpretations?"**, <https://arxiv.org/abs/2507.21168>.
   Head-to-head test of model-family diversity vs same-model-different-phrasing diversity on
   BoolQ/StrategyQA/PubmedQA. **Question-interpretation diversity beat model diversity**; model-diversity
   ensembles "typically produce results between the best and worst member with no clear improvement."
   (Exact deltas not verified.)
5. **Bugaud, "Hidden Clones: Exposing and Fixing Family Bias in Vision-Language Model Ensembles,"**
   <https://arxiv.org/abs/2603.17111> (VLM, adjacent domain). Effective ensemble size collapses to
   **2.5–3.6 "independent voters" regardless of nominal ensemble size**, with regimes where correlated
   majority errors drive accuracy to 0%.
6. **Turkmen, Buyukates, Bastopcu**, <https://arxiv.org/abs/2602.08003> — Gaussian-copula model of error
   correlation yielding an information-theoretic accuracy ceiling that explains ensemble plateaus.
7. **Mechanism**: Huh, Cheung, Wang, Isola, **"The Platonic Representation Hypothesis,"**
   <https://arxiv.org/abs/2405.07987> — representations across architectures, modalities and objectives
   converge with scale. Contested: <https://arxiv.org/abs/2602.14486> argues convergence is local not global;
   <https://arxiv.org/abs/2507.01098> proves it for deep linear nets. Disputed in detail, but it is the
   standard explanation for *why* different pipelines produce shared blind spots.
8. **Theory**: Kleinberg & Raghavan, "Algorithmic Monoculture and Social Welfare," PNAS 2021,
   <https://arxiv.org/abs/2101.05853>; Bommasani et al., "Picking on the Same Person: Does Algorithmic
   Monoculture lead to Outcome Homogenization?", <https://arxiv.org/abs/2211.13972> (component sharing
   reliably increases homogenization; magnitudes unverified).

### 4.2 Evidence that cross-family checking DOES help — and why it still does not rescue the premise

**The single most relevant paper to your experiment, and you should read it before running anything:**

**Xiang, Zhang, Zhang, Xu, "Cross-Model LLM Code Review: Should you use Claude to review Codex or vice
versa?"** <https://arxiv.org/abs/2607.21656>. 116 hard/medium LeetCode-style tasks; reviewer sees problem +
draft code and **cannot execute tests** (approximates real review conditions — and matches your setup).

| condition | pass rate | p |
|---|---|---|
| Claude reviews Codex (cross-family) | 71.6% → **89.7%** | .001 |
| Codex self-review | 71.6% → **84.5%** | .022 |
| Codex reviews Claude (cross-family) | 91.4% → **82.8%** — *got worse* | .046 |
| Claude self-review | 91.4% → **91.4%** — no change | — |

Authors' conclusion: **the benefit is asymmetric — "use Claude to review Codex, not the other way around."**
Cross-family review helped in one direction and actively *hurt* in the other. **Family difference alone
predicted neither the direction nor the magnitude; relative reviewer competence did.** Caveats: N=116, one
task domain, one model pairing — not a broad multi-family study.

Other relevant results:
- **Dai, Liang, Xu, Xie, Mechtaev**, <https://arxiv.org/abs/2511.12288> — LLM verification proxies "often
  corroborate rather than catch errors, especially when the model exhibits correlated errors." Directly on
  point for a code-verification design.
- **Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet,"**
  <https://arxiv.org/abs/2310.01798> — self-correction without external ground truth can *degrade*
  performance. Supports arm (a) being the weakest arm, but says nothing about family specifically.
- **Multi-agent debate, mostly negative:** debate "does not reliably improve accuracy"
  (<https://arxiv.org/abs/2608.03239>); "debate alone does not improve expected correctness," majority voting
  drives the gains (<https://arxiv.org/abs/2508.17536>); harmful conformity ~29% flip-to-wrong
  (<https://arxiv.org/abs/2606.00820>); degradation reported in <https://arxiv.org/abs/2604.26561> and
  <https://arxiv.org/abs/2606.07810>. **One important positive with the right shape:** Parmar et al., "When
  Helping Hurts," <https://arxiv.org/abs/2606.02866> — debate degrades *generation* by −1.6 to −15.5 pp but
  **improves error-detection F1 by +27.4 pp**. Cross-checking is better at *catching* than at *fixing*,
  which is exactly your task framing and is encouraging for the experiment.
- Correlated-error amplification in multi-agent pipelines: <https://arxiv.org/abs/2606.13197>,
  <https://arxiv.org/abs/2606.23983>, <https://arxiv.org/abs/2512.23518>.

### 4.3 What this means for the experiment

The premise is not dead, but it is **misspecified in a way that will make the result uninterpretable if you
do not fix it.** Two concrete defects:

1. **Your design confounds family with capability.** If (c) beats (b), the literature says the most likely
   explanation is that the arm-(c) model is simply a better code reviewer — not that families fail
   independently. Xiang et al. is the existence proof: the same family swap helped in one direction and hurt
   in the other. As specified, your experiment cannot distinguish these.
2. **The construct you actually care about is latent-error-correlation, not family label.** Kim et al. and
   Goel et al. both find capability/representational similarity, not vendor, predicts error overlap. And
   Q3(b) reaches the identical conclusion from the adversarial side: what carries the bridging property is
   position in latent space, not the label.

Both are fixable — see the recommendation below. Fixed, the experiment becomes *more* valuable, not less:
it would be measuring whether measured error-decorrelation (not family branding) buys you detection, which
is a question the literature poses but has not answered for agent false-success.

---

## Verified vs inferred

**Verified this session (fetched, URL live, numbers read off the source):**
- PIT's default vs equivalent-prone operator classification, with PIT's own wording.
- Google mutation-testing numbers: arid-mutant definition; 820 → 77 → 7 median mutants; 85% initially
  unproductive → 82% productive, 80%→89%; 7×-files cap; AOR/LCR/ROR/SBR/UOI with ROR 84.1%, AOR ~79%,
  UOI 74.5%. MuRS 11.45% vs 12.41%.
- Facebook study: learned error-inducing patterns from real errors/incidents; >50% mutant survival;
  ~half of 26 developers would act.
- Straubinger et al. <10% equivalent; Meta LLM equivalent-mutant detector 0.79 P / 0.47 R.
- The 2606.15689 synthetic-vs-real collapse: F1 0.847 → 0.066, 92% degradation, 5 models named.
- Terminal Wrench: 1,968 tasks audited, 323 (16%) hackable, 3,632 hack trajectories.
- HackDetect: 2,385 traces, 15 benchmarks, 67% / 66.7%, inflation 0.45–1.00.
- All Q2 numbers — computed here, reproducible from `scratchpad/power.py`.
- Q3(a): the r̂ formula, λᵢ=0.15 / λf=0.03, iₙ≥0.40 / |fₙ|<0.50, Apache-2.0, Python, no packaging.
- Q3(b): title, authors, 2026-07-02, $30.50, 10.7% with <10 ratings.
- Q3(c): title, Stray et al., 2026-03-20, N=9,386, six arms, bridging-alone null, +detox ~0.042 SD and
  Add News ~0.044 SD both p<0.05, pooled ~0.027 SD.
- Q4: Kim et al. 60% error agreement / 350+ models; Goel et al. CAPA, r≈0.84, partials 0.35–0.65, the
  Qwen-72B 71% vs Llama-70B 67% example; Panickssery 0.912 / 0.705 / τ up to 0.82 and the Llama-2 caveat;
  Xiang et al. full 4-row table with p-values; Parmar +27.4 pp detection F1.

**Inferred, recalled, or not fully verified — treat with caution:**
- Just et al. FSE 2014 mutant/real-fault coupling percentages. URL is live but the PDF would not decode and
  Semantic Scholar rate-limited. Direction corroborated by <https://arxiv.org/abs/2103.07189>; **do not cite
  a specific percentage** without re-fetching.
- **Trivial Compiler Equivalence (TCE)** — recalled from prior knowledge (Papadakis et al., ICSE 2015).
  **Zero arXiv hits for the phrase.** No verified URL. Pointer only. (Also Python-inapplicable.)
- Cosmic-ray's full operator list — the docs pages 404'd or did not enumerate operators; only `NumberReplacer`
  was confirmed. The Tier A/B taxonomy above is built on PIT and Google, which are better-evidenced anyway.
- mutmut's operator list — docs only give examples (integer literal +1, `<`→`<=`, `break`↔`continue`) and
  point at `node_mutation.py`. Notably mutmut *does* offer type-checker-based mutant filtering, which is a
  useful primitive for your Tier-C exclusion.
- Per-arm N breakdown in Q3(c) (doesn't sum to 9,386).
- Bommasani et al. homogenization magnitudes; LLM-TOPLA ensemble gains; Rosales & Miret exact deltas —
  abstract-level only.
- Terminal Wrench and HackDetect **dataset download URLs** — release is stated/implied but no direct link
  was found. Verify availability before planning around them.
- Several 2026 arXiv entries surfaced via the arXiv API were summarised by an intermediate model; the five
  papers most load-bearing for decisions (2606.15689, 2606.08960, 2607.22368, 2607.01824, 2603.19626,
  2607.21656, 2502.04313) were re-fetched individually. Lower-tier citations in Q4 §4.2 (the debate
  literature) were not individually re-verified.

**Method limitation:** the session's WebSearch budget was exhausted (200/200) at the start of this task. All
research was done through WebFetch against the arXiv API, arXiv abstract/HTML pages, GitHub raw, and vendor
docs. No general web search was performed, so non-arXiv sources (blogs, news, industry write-ups) are
underrepresented, and negative results ("no such thing exists") are weaker than they would otherwise be.

---

## Recommendation for the experiment design

Ordered by how much each changes the design.

**1. Fix the family/capability confound before anything else. (Highest priority.)**
As specified, a positive (c)-vs-(b) result is fully explained by "the other model is a better reviewer."
Xiang et al. (<https://arxiv.org/abs/2607.21656>) shows the same family swap helping in one direction and
hurting in the other. Two fixes, use both if you can:
- **Run both directions.** Model X reviews artifacts produced by Y, *and* Y reviews artifacts produced by X.
  If cross-family beats same-family in both directions, family is doing real work. If only one direction,
  you have measured a capability gap and should say so.
- **Match reviewers on capability** using a common code-review benchmark, and report the match.

**2. Add a pre-registered measurement of error correlation itself.**
Compute **CAPA / κₚ** (<https://arxiv.org/abs/2502.04313>) between the arm-(b) and arm-(c) reviewers on your
items. Q4 says representational similarity, not family label, is the operative variable. Without this, a null
result is uninterpretable — you will not know whether the design failed or whether the two "different
families" simply have correlated errors. With it, a null becomes a *finding*: "family diversity bought no
error decorrelation, κₚ = 0.7." Cheap to add, and it converts your biggest risk into your most citable result.

**3. Use the kill-test certificate for ground truth (§1.2).** Only keep mutants killed by the repo's own
tests; withhold the test result from reviewers. This eliminates equivalent mutants automatically and with no
adjudication. Discard survivors.

**4. Restrict to Tier A operators (§1.3): ROR, LCR, SBR, AOR, UOI plus argument-swap.** Explicitly exclude
Tier B (Remove Conditionals, Inline Constant on arbitrary literals, Constructor→null, Non-Void→default,
Member Variable removal, Void Method Call removal, Increments on dead counters). Also exclude any mutant
whose falsified behaviour is not asserted by the completion claim — the arid-mutant test, which is a stronger
and more important filter than the equivalence test.

**5. Add a reverse-the-fix stratum from your own bug-fix history.** Facebook's approach
(<https://arxiv.org/abs/2010.13464>) and the 2606.15689 synthetic-vs-real collapse both say the same thing:
operator-generated mutants are not the real defect distribution. Pre-register that you report the synthetic
and real strata **separately and never pooled**.

**6. Pilot 30 items before committing n.** You need p_b (probably ≫ your assumed 0.4–0.6, per §1.6) and ψ,
which drives paired n entirely. If p_b lands above ~0.8, make the mutants harder or the experiment is dead
on a ceiling effect.

**7. Paired design; McNemar exact/mid-p as primary; mixed-effects logistic (`detected ~ arm + (1|item)`) as
the pre-registered full model.** Single primary endpoint (c) vs (b) at α = 0.05; (a) and (d) secondary with
CIs and no inferential claim. If you want FWER control, Dunnett against (b) as control, else Holm. Budget
**60–120 items** for Δ = 0.20.

**8. Check Terminal Wrench (<https://arxiv.org/abs/2606.08960>) and HackDetect
(<https://arxiv.org/abs/2607.22368>) before building the harness.** Terminal Wrench's 3,632 labelled hack
trajectories across 323 environments are genuine false-success artifacts with ground truth. If reusable, you
skip the entire manufacturing problem and get *real* rather than synthetic false success — which also solves
recommendation 5. Worth a day of investigation before spending weeks on mutation tooling.

**9. Keep the Community Notes / bridging leads out of scope for this experiment.** All three Q3 leads are
about aggregating many raters into a quorum; this experiment has one reviewer per arm. They belong to a later
quorum design. Two things carry forward and only two: (i) a diversity requirement stated over *labels* is
satisfiable by entities identical in *latent space* (Q3(b), and the same conclusion as Q4) — so if you ever
build a family-diversity quorum, gate on measured error-decorrelation, not on vendor names; (ii) one good RCT
(<https://arxiv.org/abs/2603.19626>) found bridging-alone null, so expect a bridging quorum to need a second
component.

**10. Reframe the headline question.** "Does a different model family catch false success better?" is, per
Q4, probably the wrong question — family is a weak proxy. "Does *measured error decorrelation* between
generator and reviewer predict false-success detection, and is model family a usable proxy for it?" is the
same experiment, costs no extra items given recommendation 2, and is answerable either way. It also survives
a null result, which the current framing does not.

---

## Sources

**Mutation testing**
- PIT mutation operators (default vs equivalent-prone): <https://pitest.org/quickstart/mutators/>
- Petrović, Ivanković, Fraser, Just — *Practical Mutation Testing at Scale* (arid mutants, 820→77→7,
  operator productivity): <https://arxiv.org/abs/2102.11378>
- Petrović, Ivanković, Fraser, Just — *Does mutation testing improve testing practices?* (15M mutants,
  coupling to real faults): <https://arxiv.org/abs/2103.07189>
- Chen et al. — *MuRS: Mutant Ranking and Suppression using Identifier Templates* (11.45% vs 12.41%;
  statement-deletion variance): <https://arxiv.org/abs/2306.09130>
- Beller, Wong, Bader, Scott, Machalica, Chandra, Meijer — *What It Would Take to Use Mutation Testing in
  Industry — A Study at Facebook*: <https://arxiv.org/abs/2010.13464>
- Straubinger, Degenhart, Fraser — *An Empirical Evaluation of Manually Created Equivalent Mutants* (<10%):
  <https://arxiv.org/abs/2404.09241>
- Foster, Gulati, Harman et al. — *Mutation-Guided LLM-based Test Generation at Meta* (equivalent-mutant
  agent, 0.79 P / 0.47 R): <https://arxiv.org/abs/2501.12862>
- Tian, Shu, Wang et al. — *LLMs for Equivalent Mutant Detection: How Far Are We?*:
  <https://arxiv.org/abs/2408.01760>
- Garg, Ojdanic, Degiovanni et al. — *Cerebro: Static Subsuming Mutant Selection* (68% fewer equivalent
  mutants): <https://arxiv.org/abs/2112.14151>
- Just, Jalali, Inozemtseva, Ernst, Holmes, Fraser — *Are mutants a valid substitute for real faults?*
  FSE 2014 (**numbers unverified this session**):
  <https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf>
- mutmut documentation (type-checker-based mutant filtering): <https://mutmut.readthedocs.io/en/latest/>
- cosmic-ray operator documentation (did not enumerate operators):
  <https://cosmic-ray.readthedocs.io/en/latest/how-tos/operators.html>

**False-success / overclaiming corpora and LLM code review**
- Zhong, Segal, Bercovich, Saxena, Zhang, Raghunathan — *Hardening Agent Benchmarks with Adversarial
  Hacker-Fixer Loops* (Terminal Wrench: 323 environments, 3,632 hack trajectories):
  <https://arxiv.org/abs/2606.08960>
- Shao, Chen, Zhang, Pan, Luo — *Do Agent Benchmarks Measure Capability? Protocol Validity in the Age of
  Agentic AI* (HackDetect, 2,385 traces, 15 benchmarks): <https://arxiv.org/abs/2607.22368>
- Desai et al. — *SWE-Marathon* (13.8% reward hacking): <https://arxiv.org/abs/2606.07682>
- *Diff-Based Code Corruption using LLMs for Large-Scale Bugfix Benchmarking* (MegaBugFix, 12,629 buggy
  Python programs): <https://arxiv.org/abs/2606.29088>
- *SWE-Bench ProMax* (~60% of unsolved SWE-bench Verified instances have flawed tests):
  <https://arxiv.org/abs/2608.09802>
- Kumar, Bararia, Raj — *Bigger Isn't Always Better: A Comparative Evaluation of LLMs for Automated Code
  Review* (**synthetic F1 0.847 vs real-PR F1 0.066**): <https://arxiv.org/abs/2606.15689>
- Xiang, Zhang, Zhang, Xu — *Cross-Model LLM Code Review: Should you use Claude to review Codex or vice
  versa?*: <https://arxiv.org/abs/2607.21656>
- Dai, Liang, Xu, Xie, Mechtaev — *Reducing Hallucinations in LLM-Generated Code via Semantic Triangulation*:
  <https://arxiv.org/abs/2511.12288>

**Bridging / Community Notes (Q3)**
- Community Notes ranking documentation (r̂ formula, λᵢ=0.15, λf=0.03, thresholds):
  <https://github.com/twitter/communitynotes/blob/main/documentation/under-the-hood/ranking-notes.md>
  / <https://communitynotes.x.com/guide/en/under-the-hood/ranking-notes>
- Community Notes source (Python, Apache-2.0): <https://github.com/twitter/communitynotes>
- Warden — *Understanding Bridge Based Ranking*: <https://jonathanwarden.com/understanding-bridge-based-ranking>
  (companion Julia implementation: `social-protocols/bridge-based-ranking`)
- Selvam, Baxter, Hilgard, Miller, Coleman, Vitercik, Koyejo — *Gaming Consensus: Coordinated Manipulation in
  Crowdsourced Fact-Checking* ($30.50/note; 10.7% with <10 ratings): <https://arxiv.org/abs/2607.01824>
- Stray et al. — *The Prosocial Ranking Challenge* (N=9,386; bridging-alone null; +detox ~0.042 SD):
  <https://arxiv.org/abs/2603.19626>

**Model-family error correlation (Q4)**
- Kim, Garg, Peng, Garg — *Correlated Errors in Large Language Models* (ICML 2025; 350+ models; 60% error
  agreement; capability > provider): <https://arxiv.org/abs/2506.07962>
- Goel, Struber, Auzina, Chandra, Kumaraguru, Kiela, Prabhu, Bethge, Geiping — *Great Models Think Alike and
  this Undermines AI Oversight* (CAPA; r≈0.84 judge affinity): <https://arxiv.org/abs/2502.04313>
- Panickssery, Bowman, Feng — *LLM Evaluators Recognize and Favor Their Own Generations* (0.912/0.705; τ≤0.82):
  <https://arxiv.org/abs/2404.13076>
- Rosales, Miret — *Diverse LLMs or Diverse Question Interpretations?*: <https://arxiv.org/abs/2507.21168>
- Bugaud — *Hidden Clones: Family Bias in VLM Ensembles* (2.5–3.6 effective voters):
  <https://arxiv.org/abs/2603.17111>
- Turkmen, Buyukates, Bastopcu — *Don't Always Pick the Highest-Performing Model*:
  <https://arxiv.org/abs/2602.08003>
- Huh, Cheung, Wang, Isola — *The Platonic Representation Hypothesis*: <https://arxiv.org/abs/2405.07987>
  (critique: <https://arxiv.org/abs/2602.14486>; proof for linear nets: <https://arxiv.org/abs/2507.01098>)
- Kleinberg, Raghavan — *Algorithmic Monoculture and Social Welfare* (PNAS 2021):
  <https://arxiv.org/abs/2101.05853>
- Bommasani, Creel, Kumar, Jurafsky, Liang — *Picking on the Same Person: Does Algorithmic Monoculture lead to
  Outcome Homogenization?*: <https://arxiv.org/abs/2211.13972>
- Huang, Chen, Mishra, Zheng, Yu, Song, Zhou — *Large Language Models Cannot Self-Correct Reasoning Yet*:
  <https://arxiv.org/abs/2310.01798>
- Parmar et al. — *When Helping Hurts* (debate: −1.6 to −15.5 pp generation, **+27.4 pp error-detection F1**):
  <https://arxiv.org/abs/2606.02866>
- Choi, Zhu, Li — *Debate or Vote*: <https://arxiv.org/abs/2508.17536>
- Shen et al. — *Relational Priors as Convergence Pressure in LLM-Based Multi-Agent Systems*:
  <https://arxiv.org/abs/2608.03239>
- Hao et al. — *Not All Flips Are Conformity* (~29% flip-to-wrong): <https://arxiv.org/abs/2606.00820>
- Niu, Zhang — *ARMOR-MAD* (fixed debate pipelines amplify correlated errors):
  <https://arxiv.org/abs/2606.13197>

**Computation**
- Power tables in Q2 computed by `scratchpad/power.py` (two-proportion z with Casagrande–Pike–Smith
  continuity correction; McNemar normal approximation), α=0.05 two-sided, power=0.80.
