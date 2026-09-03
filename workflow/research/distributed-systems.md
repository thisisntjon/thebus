# thebus — Distributed-Systems Prior Art: What to Copy, What to Simplify, What Will Bite Us

Date: 2026-08-18
Question: which battle-tested distributed-systems mechanisms should thebus copy exactly, and what are the known failure modes of the ones we have already half-invented?

Framing note used throughout: thebus is an **asynchronous system with unbounded pauses** (an agent can be blocked on a model call, rate-limited, or killed mid-turn), running on a **non-linearizable store** (GitHub reads lag writes), with **no server-side compare-and-swap on the issue API**. That combination is exactly the environment for which the literature has hard answers — and it is exactly the environment in which lease-based mutual exclusion is *unsafe without fencing*.

---

## What I found

### 1. LEASES

#### 1a. The real numbers, and the ratio that actually matters

| System | Lease / session length | Renewal interval | Grace / detection budget | Ratio (lease ÷ renew) |
|---|---|---|---|---|
| Chubby | 12 s default lease extension | KeepAlive is a *blocked call*: the master holds the RPC open and answers just before expiry, so effectively ~12 s | 45 s client grace period across master failover | ~1 (but see below) |
| ZooKeeper | negotiated, clamped to `[2 × tickTime, 20 × tickTime]` = 4 s–40 s at default `tickTime=2000` | client pings at ~1/3 of the negotiated timeout | none — session expiry deletes ephemeral znodes | ~3 |
| etcd | lease TTL, floor tied to election timeout (`min TTL = ceil(3 × election-timeout / 2)`); election timeout 1000 ms default, heartbeat 100 ms | `KeepAlive` stream, client-driven | election timeout ≥ 10 × RTT; max sane election timeout 50 s | 10 (heartbeat ÷ election) |
| Kubernetes node lease | `nodeLeaseDurationSeconds` = 40 s | kubelet renews at 0.25 × duration = every 10 s; `--node-status-update-frequency` also 10 s | controller `node-monitor-grace-period` 40 s, checked every `node-monitor-period` 5 s | 4 |
| Kubernetes leader election (client-go) | `LeaseDuration` 15 s | `RetryPeriod` 2 s, with `RenewDeadline` 10 s | invariant: `LeaseDuration > RenewDeadline > RetryPeriod × JitterFactor(1.2)` | ~7 |

The generalizable law is not any specific number, it is the **three-parameter shape**, which every one of these systems has independently converged on:

1. **Lease duration** L — how long the seat stays held without contact.
2. **Renewal interval** R — how often the holder tries. Everyone picks **R ≈ L/3 to L/4**, i.e. *the holder gets 3–4 independent chances to renew before it loses the seat*. Kubernetes is explicit: the default is tuned so "the kubelet tries 5 times before the node is declared unhealthy."
3. **Renew deadline** D — a separate, *earlier* deadline at which the **holder voluntarily stops acting** because it can no longer prove it still holds the lease. Kubernetes makes this a first-class parameter (`RenewDeadline` 10 s < `LeaseDuration` 15 s). This is the parameter thebus is most likely to be missing.

The invariant `L > D > R × jitter` is the thing to copy verbatim. Its meaning: **the holder must give up before the reaper takes it away**, with a margin at least as wide as one failed renewal round plus jitter. Without D, the holder and the reaper disagree during the window `[D, L]` and you get two actors on one seat.

#### 1b. Clock skew

None of these systems compare wall clocks across machines for lease safety.

- **Chubby** deliberately uses *asymmetric* timing: the client's local view of the lease is conservative (it assumes its clock runs fast relative to the master's), so the client believes the lease expires *before* the master does. Combined with the blocked KeepAlive, the client is always the pessimist.
- **etcd** sidesteps skew on leader change by simply **renewing all leases after a new election** rather than trying to reconstruct absolute expiry times across a skewed cluster.
- **Kubernetes** node leases carry `renewTime` written by the *API server's* view via the object, and the controller compares against its own monotonic observation window — one clock, not N.

The pattern: **one authoritative clock (the store's), plus each holder being the pessimist about its own lease.**

For thebus, GitHub timestamps every comment server-side. That is the one authoritative clock. **Never** let an agent write its own `expires_at` computed from its local clock; write `heartbeat_at` and let the reaper compute expiry from GitHub's `created_at` on the heartbeat comment.

#### 1c. "Is it slow or dead" — lease expiry ≠ death

This is the load-bearing insight and every mature system says the same thing: **you cannot distinguish a slow member from a dead one, so stop trying.** Lease expiry is a *decision*, not an *observation*.

- Chubby's answer: the session ends, and the *client library* is responsible for telling the application it lost its locks. Chubby also adds **`lock-delay`** (typically 1 minute): after a lock is released *abnormally* (session death rather than an explicit release), the lock cannot be re-acquired by anyone for the delay period. That is a pure "give the zombie time to notice it's dead" buffer.
- Kubernetes' answer: a node whose lease expired is marked unhealthy and its pods are evicted — the system acts as if it were dead and relies on the kubelet's own `RenewDeadline` discipline to have already stopped it.
- SWIM's answer: an explicit intermediate state, **SUSPECT**, which the suspected member can **refute** (see §3).
- Kubernetes v1.36 (alpha, `ControllerManagerReleaseLeaderElectionLockOnExit`) adds the complementary optimization: on *clean* exit, actively release the lock rather than wait out the TTL. Graceful release and timeout expiry are two different paths and both need to exist.

thebus is missing at least two of these three: a SUSPECT state, and a lock-delay after abnormal seat release.

#### 1d. Fencing — do we need it? Yes, and we already have the token.

Kleppmann's argument applies to thebus *more* strongly than to a database client, because our "process pause" is not a 100 ms GC pause, it is **a model call that can hang for minutes, or an agent that resumes from a stale context window and acts on beliefs formed before its lease died.** His scenario is literally ours:

> "Client 1 acquires the lease and gets a token of 33, but then it goes into a long pause and the lease expires. Client 2 acquires the lease, gets a token of 34... Clients 1 and 2 now both believe they hold the lock."

and

> "GC can pause a running thread at *any point*, including the point that is maximally inconvenient for you (between the last check and the write operation)."

The fix is not a better lock. The fix is that **the resource** — not the lock service — **rejects stale work**:

> "the storage server remembers that it has already processed a write with a higher token number (34), and so it rejects the request with token 33."

Real production fencing tokens:
- **Chubby sequencers**: an opaque string containing the lock name, **lock generation number** (bumped on every free→held transition), and mode. The client passes it to the downstream file server, which validates it. For servers that can't validate, Chubby falls back to `lock-delay`.
- **ZooKeeper**: `zxid` or the znode `version` field is the token.
- **Kafka**: `transactional.id` + **producer epoch**. Re-registering the same transactional id bumps the epoch; any producer writing with an older epoch is rejected as a zombie (`ProducerFencedException`). Kafka's **controller epoch** does the same for split-brain controllers: the epoch rides in every request, and brokers trust the highest.

**thebus already mints a perfect fencing token and is currently throwing it away.** GitHub allocates issue and comment numbers server-side, monotonically, per repository. A `seat_epoch` = the issue/comment number of the *lease-grant* event is monotonic, globally ordered by GitHub, unforgeable by an agent, and free. The tie-break we already invented ("lowest issue number wins") is the *same* number used for a *different* purpose — we discovered the token's ordering property and used it for conflict resolution but not for fencing.

**COPY EXACTLY**
- The three-parameter lease shape with the invariant `LeaseDuration > RenewDeadline > RetryPeriod × 1.2`, and `RenewDeadline` as a real, enforced, holder-side stop signal.
- Renewal at **L/4**, so a holder gets ~4 shots. Given GitHub API latency and rate limits (seconds, not milliseconds) and agent turn lengths (minutes), the analogue of "10× RTT" puts L in the **15–45 minute** band with R at 4–10 minutes — not seconds.
- Chubby's **lock-delay** after abnormal release: a cooldown before the seat can be re-leased. This is the single cheapest safety mechanism available to us and it needs no new primitives.
- A **fencing token = the GitHub-allocated number of the lease-grant event**, stamped into every work product the seat-holder writes.
- The client-side pessimist rule: the holder's own view of its lease expires *before* the reaper's.

**SIMPLIFY**
- Don't build a keepalive stream or blocked-RPC (Chubby's trick exists to save RPCs at Google scale; we have minutes of budget).
- Don't negotiate lease lengths per member (ZooKeeper's clamped negotiation); one constant per seat class is enough.
- Don't try to handle clock skew analytically. Only GitHub's server timestamps count. Agents never write absolute expiry times.

**FAILURE MODE WE ARE WALKING INTO**
1. **No RenewDeadline** → a holder whose heartbeat write silently failed keeps working past its own expiry while the reaper tombstones it. Two agents, one seat, both convinced they're legitimate. This is the classic split-brain and it is *guaranteed* to happen at our timescales, not merely possible.
2. **No fencing** → even a correct lease is unsafe. The reaped agent's next write lands *after* the tombstone and after the new holder's first write. Because our ledger is append-only and read by other agents as ground truth, a post-tombstone write from a dead holder is not just a lost update — it is **an authoritative-looking instruction injected into the roster reconstruction path.**
3. **No lock-delay** → instant re-lease after reaping maximizes the overlap window.
4. **Lease length chosen from intuition rather than from `L ≥ k × observed_write_latency`** → either flapping (too short) or seats parked for hours after real death (too long).

---

### 2. TOMBSTONES

We invented tombstones for the right reason and the reasoning matches the literature: in an eventually-consistent, replica-reading system, **a deletion that leaves no trace is indistinguishable from an entry that never existed**, so it gets resurrected. Our specific framing — "agents reconstitute the roster by reading documents, so a deleted name reads as an oversight and gets re-summoned" — is *isomorphic to Cassandra's zombie-data problem*, with the agent's context window playing the role of the stale replica.

#### 2a. Cassandra / Dynamo

- `gc_grace_seconds` default **864000 s (10 days)**. Purpose: give unreachable replicas time to learn about the delete before the tombstone itself is collected.
- The zombie rule: **if a replica is down longer than `gc_grace_seconds` and rejoins, its un-deleted data is repaired back onto the cluster and the deleted row reappears.** Safe reduction of `gc_grace_seconds` requires repair to run *more frequently* than the grace period.
- Tombstone accumulation is a real operational failure, not a theoretical one: `tombstone_warn_threshold` 1000, `tombstone_failure_threshold` 100000 — queries scanning that many tombstones are *failed outright* to protect the cluster.

The transferable invariant: **tombstone lifetime must exceed the maximum staleness of any reader.** In thebus, the readers are agents with context windows and cached documents. Our equivalent of "run repair more often than gc_grace" is: *every agent must re-read the roster more recently than the tombstone retention period.* If tombstones are ever pruned, that becomes a hard requirement, not a hope.

#### 2b. CRDT tombstones

- OR-Set and sequence CRDTs accumulate tombstones that are **never garbage collected** in the naive formulation; document size becomes proportional to *edit history*, not live data.
- The escape hatches: **causal stability** (a tombstone can be dropped once every replica has observed the delete — requires knowing the full replica set), **dotted version vectors / causal CRDTs** (compare causal contexts instead of storing tombstones), and **delta-CRDTs** (GC the delta and the tombstone goes with it).

#### 2c. Membership tombstones (Consul/Serf) — closest analogue to a seat roster

Serf distinguishes **failed** (suspected dead, keep trying) from **left** (graceful departure) and reaps each on a different timer: `reconnect_timeout` (**default 72 hours**) for failed nodes, `tombstone_timeout` for left nodes. `force-leave -prune` is the manual override. Two states, two clocks, plus an admin escape hatch — that is the whole design.

**COPY EXACTLY**
- **Two departure classes with different retention**: graceful retirement (`left`) vs. reaped-on-expiry (`failed`). They carry different information and deserve different lifetimes. thebus currently appears to have one tombstone kind.
- A **finite, documented retention** with an explicit reader-staleness argument attached to it, in the Cassandra style. "We keep tombstones for N because no agent's roster read is older than N/2."
- A manual **prune** escape hatch (Serf's `force-leave -prune`) so a human can excise a tombstone deliberately rather than have the ledger rot.

**SIMPLIFY**
- Do not build causal-stability GC. We can't cheaply know "every reader has seen this," and our tombstone volume is tiny (members, not rows).
- Do not build delta-CRDT machinery. Our merge is human/LLM-mediated, not algebraic.
- Given our volume, **retaining tombstones forever in the issue log is defensible** — the append-only ledger is the point. The growth problem is not bytes, it is **attention** (see failure mode 2 below).

**FAILURE MODE WE ARE WALKING INTO**
1. **Resurrection via stale reader.** Our stated mechanism ("a deleted name reads as an oversight") is precisely Cassandra's zombie. Tombstones fix it *only if the reader reads the tombstone*. An agent that reads a **cached or truncated** roster, or reads only the top N comments of a long issue, gets the pre-tombstone view and re-summons the member. **Tombstones do not protect a reader who never reads them** — this is the failure mode we are most likely to hit and least likely to detect, because it looks like an agent being helpful.
2. **Tombstone-scan overload, in context-window units.** Cassandra fails queries at 100k tombstones. Our budget is thousands of tokens. A roster issue that is 80% tombstones will get truncated by *some* reader, which reintroduces (1). The Cassandra lesson — "too many tombstones is itself an outage" — transfers directly with the threshold reduced by five orders of magnitude. Mitigation: keep a **compacted roster head** (current seats + one-line tombstone index) separate from the full append-only history, and make the head the canonical read.
3. **Tombstone without an incarnation number** (see §3) means we cannot distinguish "this member is retired" from "this member retired and came back," so a legitimate rejoin is either blocked or silently overwrites the tombstone.

---

### 3. MEMBERSHIP PROTOCOLS

#### 3a. SWIM, and its numbers

memberlist (Serf/Consul/Nomad) `DefaultLANConfig`: `ProbeInterval` 1 s, `ProbeTimeout` 500 ms, `IndirectChecks` 3, `SuspicionMult` 4, `SuspicionMaxTimeoutMult` 6, `GossipInterval` 200 ms, `GossipNodes` 3, `RetransmitMult` 4, `PushPullInterval` 30 s. WAN config relaxes to `ProbeInterval` 5 s, `ProbeTimeout` 3 s, `SuspicionMult` 6, `GossipInterval` 500 ms.

Three mechanisms worth stealing wholesale:

**(i) Indirect probes before suspicion.** A direct ping timeout does *not* mean dead. The prober asks `IndirectChecks` (3) other members to ping the target on its behalf. Only if all fail does suspicion start. This separates "I can't reach you" from "you are down" — the exact distinction thebus needs, because our failures are asymmetric (an agent may be able to write to GitHub but not be readable yet, or vice versa).

**(ii) SUSPECT as a first-class state with a scale-aware timeout.**
`SuspicionTimeout = SuspicionMult × log(N+1) × ProbeInterval`, capped at `SuspicionMaxTimeoutMult × ProbeInterval`. Note the timeout **grows with cluster size** — because dissemination takes longer in a bigger cluster, so the refutation deadline must too. If thebus's seat count grows, a fixed grace period silently becomes too tight.

**(iii) Incarnation numbers — the identity mechanism.**
Every member holds an incarnation counter, **incremented only by itself**. State transitions are ordered by `(incarnation, state-precedence)`. A suspected member **refutes** by broadcasting `alive` at a higher incarnation, which supersedes the suspicion everywhere without any coordination. Crucially: **a member can never mark itself dead, and no one else can raise its incarnation.** That asymmetry is what makes the protocol convergent without consensus.

**Lifeguard** (HashiCorp's SWIM extension, in memberlist since 2017) addresses SWIM's remaining flaw — "refutation only succeeds if the refuting message is processed in a timely manner," which fails when the *suspector* is the degraded one:
- **Self-Awareness / Local Health**: a member that is itself experiencing degraded interactions (a "Node Self Awareness" counter) becomes *more reluctant* to accuse others and *more generous* with its own timeouts.
- **Dogpile**: the suspicion timeout **shrinks logarithmically as independent members confirm** the suspicion, instead of being fixed. One accuser → long deadline. Many independent accusers → short deadline.
- **Buddy System**: the suspector tells the suspected member directly, rather than waiting for gossip to reach it, so refutation can be immediate.

Reported: ~50× reduction in false positives; at default alpha=4, 20% faster detection with 20× fewer false positives.

Note the deep connection: **Dogpile is an independent-quorum mechanism applied to failure detection** — see §4.

#### 3b. Identity vs. address — the thing thebus already got right, half

- **Erlang/OTP**: "a registered name is an alias for a pid." Work is sent to a *name*; the name resolves to whichever process currently holds it; supervisors restart the process under a new pid but the same name. This is exactly the SEAT LEASE model, and it is 40 years battle-tested. OTP's supervisor default restart intensity is `intensity=1, period=5` — **more than 1 restart in 5 seconds and the supervisor gives up and escalates.** That is a circuit breaker on crash-loops, and thebus has no analogue: nothing currently stops a seat from being leased and reaped in a tight loop forever.
- **Akka Cluster**: a member is `(Address, UID)`. The UID is generated fresh per ActorSystem instance. A node **downed while unreachable cannot rejoin** — the process must restart, producing a new UID. And: two members can never share an `Address`; if a node restarts at the same address, the old instance is auto-downed first. Akka *quarantines* a failed UID and dead-letters all messages to it.

The synthesis across SWIM / Akka / OTP: **three-level identity.**
1. **Seat** — the role, permanent, what work routes to. (thebus has this.)
2. **Member** — the durable identity of a participant. (thebus has this.)
3. **Incarnation / UID** — *this particular occupancy of the seat by this member*, monotonic, self-incremented on rejoin. (**thebus appears to lack this.**)

Level 3 is what makes rejoin-after-death safe and what makes tombstones unambiguous. And it is *the same number as the fencing token from §1d*.

**COPY EXACTLY**
- **Indirect probes** before declaring a seat-holder missing: before the reaper tombstones, at least one *other* member should attempt to reach the holder (post a direct ping comment), and the failure should be corroborated.
- **SUSPECT state with refutation.** Reaping must be two-phase: `SUSPECT` (visible, refutable, with a deadline) → `DEAD` (tombstone). A live-but-slow agent must have a way to say "I'm here" and have that supersede the suspicion. Right now expiry appears to go straight to tombstone.
- **Incarnation numbers, self-incremented only.** State precedence: `alive(i)` supersedes `suspect(j)` iff `i > j`; `dead` at the same incarnation always wins. Only the member itself may raise its own incarnation. Copy this rule verbatim — it is what makes the roster convergent under concurrent, lagging reads.
- **Suspicion timeout scaling with N** (`mult × log(N+1) × probe_interval`).
- **OTP restart intensity** as a crash-loop breaker: N lease-reap cycles for one seat within window T → escalate to a human instead of re-leasing.
- **Akka's rejoin rule**: a member that was tombstoned may return, but **only as a new incarnation** — never by resuming the old one.

**SIMPLIFY**
- No random-peer probing / dissemination fanout. Our "gossip" substrate is a single GitHub issue that everyone reads; dissemination is O(1) and we can skip all of SWIM's epidemic machinery. **Keep the state machine, drop the transport.**
- Lifeguard's full local-health counter is probably overkill, but see the assumption candidate below — the *self-awareness* idea (an agent that knows it's been rate-limited should be reluctant to accuse others) may be worth a one-bit version.

**FAILURE MODE WE ARE WALKING INTO**
1. **No SUSPECT state → false-positive reaping.** SWIM was published in 2002 and HashiCorp still needed Lifeguard in 2017 to make false positives tolerable. A system that goes expiry → tombstone with no refutation window will tombstone live members whenever the substrate is slow. And *our* substrate is documented to lag. The consequence is worse than in SWIM: a tombstone is a **social fact** in a ledger other agents read as authority.
2. **Tombstone + rejoin ambiguity without incarnations.** A returning member either can't come back (Akka's hard rule, but we probably want them back) or comes back in a way that makes the tombstone look wrong retroactively, corrupting the audit trail we built tombstones to protect.
3. **Reap/re-lease loop with no circuit breaker** (OTP intensity). A flaky seat can burn budget indefinitely with nobody noticing.
4. **Fixed suspicion timeout that doesn't scale with fleet size** — works at 5 seats, mass-false-positives at 50.

---

### 4. INDEPENDENCE / DOUBLE-COUNTING

Our ECHO COLLAPSE problem — "five members restating one judgment must not read as five independent findings" — is a real, named, solved problem in three separate literatures. We have re-derived the requirement; none of us has yet implemented the standard solution.

#### 4a. BFT: votes are a *set keyed by signer*, never a counter

Bracha's Reliable Broadcast (1987) is the canonical treatment and it is structurally exactly our problem: it has an explicit ECHO phase, and it must not let echoes masquerade as independent support.

- Phase structure: propose → **ECHO** → **READY** → deliver. A replica sends `READY(v)` after receiving `n−f` ECHOs for `v`, **or** after receiving `f+1` READYs for `v`.
- Safety comes from **quorum intersection**: with `n > 3f`, any two quorums of size `n−f` intersect in at least `f+1` members, so at least one honest member is in both — meaning conflicting values cannot both be certified.
- The mechanism that prevents echo-as-independent-vote is deceptively simple and universal across BFT: **you tally a set of distinct signed identities, not a count of messages.** Receiving the same signed ECHO twice adds nothing. A quorum certificate is *the collection of signatures itself*, carried as **evidence** so that any third party can re-verify the count independently rather than trusting an aggregator's claim of "5 agreed."
- The `f+1 READY → READY` rule ("amplification") is explicitly *not* an independence claim — `f+1` guarantees ≥1 honest, which is a **weaker, deliberately-labeled** threshold than the `n−f` quorum. BFT protocols are meticulous about which threshold means what.

The two rules to steal:
- **Idempotent, identity-keyed tallying.** A judgment record is a *set* of `(member_id, incarnation, statement_hash)`. Re-stating adds a duplicate entry that collapses to one.
- **Evidence travels with the claim.** Never write "quorum reached (5/7)". Write the five signed dissent references. The reader re-counts. This is the difference between a claim and a certificate, and it is the entire reason BFT certificates are transferable.

#### 4b. Causality: vector clocks, and why they're not enough

- Vector clocks / version vectors detect concurrency vs. causal descent — the right *shape* of the question ("did B form this view independently, or after reading A?").
- But Dynamo's real-world experience is a caution: clocks grow with the number of writers, so **Dynamo truncates the oldest `(node, counter)` entry past a size threshold** — which can make causally-related versions look concurrent. Riak's **sibling explosion** is the concrete pathology: without proper causal context, concurrent values duplicate combinatorially. The fix Riak landed on is **dotted version vectors**.
- The thebus-relevant transfer: our "independence" question is **provenance/lineage**, and it is answerable with a much cheaper primitive than a vector clock — **record what each member read before forming its judgment.** If member B's dissent cites A's comment, B is *causally downstream of A*, and B is not an independent dissent. This is one field (`derived_from: [comment_ids]`), not a clock.

#### 4c. Duplicate-insensitive aggregation

The gossip-aggregation literature has the exactly-analogous problem: gossip paths overlap, so naive summation double-counts. The solution class is **duplicate-insensitive sketches** (Flajolet–Martin / HyperLogLog-style): a sketch where inserting the same element twice is a no-op, and sketches merge idempotently (`Sk(S1 ∪ S2) = merge(Sk(S1), Sk(S2))`). The design principle — not the sketch — is what we want: **make the aggregation operator idempotent and commutative, so re-delivery is harmless by construction.**

#### 4d. Merkle anti-entropy

Dynamo/Cassandra reconcile replicas by exchanging **Merkle tree root hashes** over a key range; matching roots mean "in sync, no work," diverging roots trigger a recursive walk to the differing leaves. Cost is logarithmic in the divergence, not linear in the data.

For thebus this is a *reconciliation* tool, not an independence tool: a **roster digest** (hash of the canonical seat/tombstone state) that every agent echoes in its heartbeat lets us detect, in O(1) per agent, that some agent is operating on a stale roster — which is the §2 resurrection failure mode's early-warning signal.

**COPY EXACTLY**
- **Identity-keyed set tallying** with `(member_id, incarnation)` as the key. Idempotent by construction.
- **Evidence-carrying certificates.** A quorum claim must embed the referenced dissents; the count is derived, never asserted.
- **`derived_from` provenance on every judgment.** A judgment that cites another member's judgment is causally downstream and is excluded from the independence count for that claim. This is the minimal, correct implementation of ECHO COLLAPSE.
- **Distinguish threshold semantics explicitly**, BFT-style: `f+1` ("at least one independent voice") vs. `n−f` ("a majority that cannot conflict with another majority"). A strategy change should require the latter; raising an alarm should require only the former.
- **Roster digest in every heartbeat** (Merkle-lite) to detect stale readers.

**SIMPLIFY**
- No cryptographic signatures. GitHub already attributes every comment to an account, and the ledger is append-only and attributed — GitHub *is* our PKI. This is a genuine advantage over BFT settings.
- No vector clocks. Provenance edges (`derived_from`) give us causality where we need it, without the growth/truncation pathology that bit Dynamo.
- No actual HLL sketch. Just make the tally a set.

**FAILURE MODE WE ARE WALKING INTO**
1. **Counting messages instead of counting distinct signers with distinct provenance.** This is the default behavior of an LLM summarizing an issue thread, and it is precisely how five echoes become "strong consensus." Unless the tally is a mechanical, identity-keyed, provenance-filtered computation, the ECHO COLLAPSE rule is a *norm* rather than a *mechanism*, and norms lose to helpful summarizers.
2. **Correlated non-independence that provenance can't see.** BFT assumes at most `f` faulty and independent honest replicas. Our members are frequently **the same base model with the same priors**, so five agents that never read each other can *still* produce a correlated judgment. No distributed-systems mechanism handles this — quorum intersection assumes independent failure. This is a genuine gap between our setting and the borrowed one, and it argues for deliberate **heterogeneity as a quorum requirement** (a quorum must span distinct model families / distinct evidence sources), which has no prior art to copy.
3. **Truncation-induced false concurrency.** If we ever prune provenance history to save context (Dynamo's clock truncation), causally-related judgments will start looking independent — the exact failure Dynamo hit. Prune the *content*, never the provenance edges.
4. **Amplification mistaken for independence.** Bracha's `f+1 READY → READY` rule exists to make progress, not to certify support. If thebus adds any "if enough others are worried, I'm worried too" rule (and Lifeguard's Dogpile is one), it must be labeled as amplification and excluded from independence tallies.

---

### 5. READ-AFTER-WRITE RACES

Our current answer — post-write reconciliation plus a deterministic tie-break (lowest issue number wins) — is **a legitimate, named pattern, and it is the right pattern for the API surface we're using.** It is essentially *last-writer-wins with a deterministic, externally-assigned order*, i.e. the same shape as LWW registers and as Akka's "auto-down the older instance at the same address." Observed 3× in the first live run is consistent with it *working*.

But it is the fallback tier. The known hierarchy, best to worst:

**Tier 1 — Fix it at the store (make the write conditional).** S3 spent a decade telling clients to tolerate eventual consistency, then in **December 2020 made read-after-write strongly consistent for all requests, all regions, no opt-in, no cost** — because the client-side workarounds were never actually correct. The lesson: *if a strongly-consistent primitive is available, use it; do not build reconciliation logic around a weak one by choice.*

Concretely available to thebus **today, in the same repo, at no cost**:
- **Git refs are a genuine compare-and-swap register.** `git update-ref` takes an expected `<oldvalue>` and fails if it doesn't match; `--stdin` gives all-or-nothing multi-ref transactions ("if all refs can be locked with matching old-oids simultaneously, all modifications are performed; otherwise, no modifications are performed"); `git push --force-with-lease` is the same CAS over the wire, and **GitHub enforces it server-side.** A seat lease held as a ref (`refs/thebus/seats/<seat>`) would be **linearizable**, atomically claimable, and free of the entire race — with the issue log retained as the human-readable, attributed narrative.
- **GitHub Actions `concurrency` groups** provide server-side mutual exclusion with FIFO queueing (`group:` + `cancel-in-progress: false`), i.e. a real, hosted mutex we currently aren't using.

**Tier 2 — Conditional HTTP.** GitHub supports `ETag` / `If-None-Match` on GETs (and a 304 doesn't count against rate limit), but **conditional requests on unsafe methods — POST/PUT/PATCH/DELETE — are not supported** except where a specific endpoint documents it. So `If-Match` optimistic concurrency on the issues API is *not* available. This is the concrete reason our read-then-write guard is racy and cannot be fixed on that API.

**Tier 3 — Read-your-writes discipline.** The standard formulations: route reads for a key to the primary for a window after writing it; or carry the write's position/token and require reads to be at least that fresh. Our version: after writing, **re-read until our own write is visible** before treating the read as authoritative — never act on a read that doesn't contain our own most recent write. This is cheap, correct, and (from the description) not currently mandatory in thebus.

**Tier 4 — What we have: post-write reconcile + deterministic tie-break.** Correct as a convergence rule; requires that the losing writer's effects be **undoable or harmless**, which is where fencing (§1d) returns: the tie-break decides *who won*, and the fencing token is what makes downstream work from the *loser* rejectable.

**COPY EXACTLY**
- **Idempotency keys / deterministic IDs.** Derive the identity of an intended write from its content (`hash(seat, member, intent, epoch)`) so a retry after an ambiguous failure is recognizably the same write rather than a duplicate. This is the standard defense against "did my write land?" and it composes with everything above.
- **Read-your-writes as a hard rule**: never act on a read that does not reflect your own last write to that object.
- **Git-ref CAS for anything where two claims must not both succeed** (seat claims above all). Copy `--force-with-lease` semantics exactly.
- Keep the deterministic tie-break — it is correct — but demote it from *primary mechanism* to *reconciliation backstop*.

**SIMPLIFY**
- Don't build a Paxos/Raft layer. Git refs already give us the linearizable register, and GitHub already runs the consensus.
- Don't build vector clocks for this either; monotonic GitHub-assigned numbers are a total order already.

**FAILURE MODE WE ARE WALKING INTO**
1. **Tie-break resolves the record but not the side effects.** Both claimants may have *already acted* by the time reconciliation runs. Without fencing at the resource, the loser's work products stay in the ledger looking authoritative. Reconciliation converges the *lease*, not the *world*. This is the single largest gap.
2. **Building sophisticated eventual-consistency handling on an issue API while a linearizable CAS (git refs) sits unused in the same repository.** This is the S3 lesson in miniature.
3. **Retry-without-idempotency-key on ambiguous writes** → duplicate lease grants, duplicate tombstones, duplicate dissents (which then inflate a quorum count — §4 failure mode 1 fires).
4. **Observed 3× in one run** is a rate, not an anomaly. Any guard whose correctness depends on a read being fresh will fail at roughly that rate, forever, and the frequency scales with fleet size and write rate.

---

## Verified vs inferred

**Verified (sourced, with URLs in §Sources):**
- Chubby: 12 s default lease extension; 45 s client grace period; KeepAlives held open at the master until just before expiry; sequencers containing lock name + generation number + mode, validated by the downstream server; `lock-delay` typically one minute for servers that can't check sequencers.
- ZooKeeper: session timeout clamped to `[2 × tickTime, 20 × tickTime]`, i.e. 4 s–40 s at default `tickTime=2000`; ephemeral znodes deleted on session expiry.
- etcd: heartbeat 100 ms, election timeout 1000 ms defaults; election timeout ≥ 10 × RTT; 50 s practical max; lease TTL floor tied to election timeout (`ceil(3 × election-timeout / 2)`); leases renewed after a new election to avoid cross-node clock reasoning.
- Kubernetes: `nodeLeaseDurationSeconds` 40 s, renewed at 0.25× = every 10 s; `--node-status-update-frequency` 10 s; `node-monitor-period` 5 s; `node-monitor-grace-period` 40 s. client-go leader election: `LeaseDuration` 15 s, `RenewDeadline` 10 s, `RetryPeriod` 2 s, `JitterFactor` 1.2, with the ordering invariant. v1.36 alpha lock-release-on-exit.
- Kleppmann: fencing-token argument, the token-33/34 scenario, GC-pause-at-worst-moment, the requirement that the *resource* reject stale tokens, Redlock's timing/`gettimeofday` critique.
- Kafka: transactional-id + producer epoch zombie fencing; controller epoch for split-brain.
- Cassandra: `gc_grace_seconds` 864000 default; zombie resurrection when a node is down longer than the grace period; `tombstone_failure_threshold` 100000.
- CRDTs: OR-Set/sequence tombstone accumulation; causal stability; dotted version vectors; delta-CRDT GC.
- memberlist: exact `DefaultLANConfig` / `DefaultWANConfig` / `DefaultLocalConfig` values; `SuspicionTimeout = SuspicionMult × log(N+1) × ProbeInterval`.
- Lifeguard: three mechanisms; ~50× false-positive reduction; alpha=4 default gives 20% faster detection and 20× fewer false positives.
- SWIM: incarnation numbers incremented only by the member itself; refutation via `alive` at higher incarnation.
- Serf/Consul: failed vs left; `reconnect_timeout` default 72 h; `tombstone_timeout`; `force-leave -prune`.
- Akka: `(Address, UID)` membership; downed node cannot rejoin without process restart; no two members may share an Address; quarantine dead-letters a failed UID.
- Erlang/OTP: supervisor `intensity=1, period=5` defaults; registered name is an alias for a pid; `global` replicates the name table on every node.
- Bracha RBC: propose/ECHO/READY/deliver; `n−f` ECHOs or `f+1` READYs → READY; `n > 3f` gives quorum intersection ≥ `f+1`.
- Dynamo: vector-clock truncation of the oldest `(node, counter)` entry past a threshold; Riak sibling explosion; dotted version vectors as the fix; Merkle-root exchange for anti-entropy.
- Duplicate-insensitive sketches: composability/idempotence definition (`Sk(S) = Sk(B(S))`, `Sk(S1 ∪ S2) = merge(...)`).
- S3: strong read-after-write consistency for all requests since 1 Dec 2020, no opt-in, no cost; overwrite-PUT and DELETE were eventually consistent before that.
- Git: `update-ref` with expected old value; `--stdin` all-or-nothing transaction semantics; `push --force-with-lease` as CAS.
- GitHub: `ETag`/`If-None-Match` supported on reads with 304s not counting against rate limit; **conditional requests on POST/PUT/PATCH/DELETE not supported** except where an endpoint documents otherwise.
- GitHub Actions: `concurrency` groups give single-job-at-a-time with FIFO-ish queueing when `cancel-in-progress: false`.

**Inferred (my reasoning, not sourced):**
- That GitHub-allocated issue/comment numbers are per-repo monotonic and server-assigned, and therefore usable as a fencing token. Strongly believed and consistent with our observed "lowest issue number wins" tie-break, but **not verified against GitHub documentation** — verify before building on it, especially the behavior of issue numbers across transfers and of comment IDs (which are global, not per-repo, but still monotonic in practice).
- The mapping "stale agent context window ≈ stale Cassandra replica" and the resulting requirement "every agent's roster read must be fresher than tombstone retention."
- The lease-length recommendation of 15–45 min with 4–10 min renewal. Derived by applying the systems' own ratio rules to our latency scale, not measured. **Should be derived from thebus's actual observed write-visibility latency distribution.**
- The claim that a git ref would be a linearizable seat register *as GitHub implements it*. Git's semantics are CAS; GitHub's server-side enforcement of `--force-with-lease` on push is documented behavior of the git protocol, but GitHub's *ref-update API* (`PATCH /git/refs`) does **not** obviously expose an expected-old-sha parameter — so this likely requires pushing over the git protocol rather than the REST API. **Verify before designing around it.**
- That homogeneous base models break BFT's independent-failure assumption. Analytically sound, but no source; no prior art to copy.
- The suggested "compacted roster head + full history" split.

---

## Surprises

1. **Chubby already invented fencing tokens in 2006 and called them sequencers — and shipped a fallback (`lock-delay`) for resources that can't validate them.** Kleppmann's 2016 argument is usually read as "leases are broken"; the more useful reading is "Google shipped both the token and the degraded-mode fallback on day one." thebus can have both, cheaply.

2. **Everyone converged on renewal ≈ lease/3–lease/4, but only Kubernetes made `RenewDeadline` an explicit, separate parameter.** The holder-side stop deadline is the least-copied and most-important part of the design. It is also the part thebus most likely lacks.

3. **The suspicion timeout grows with cluster size** (`mult × log(N+1) × interval`). A grace period tuned for 5 seats is wrong for 50 — silently, and in the false-positive direction.

4. **Lifeguard's Dogpile is our INDEPENDENT QUORUM rule applied to failure detection, and it explicitly requires the confirmations to be independent.** The same idea shows up in two of our five topics. That is evidence the underlying primitive — *tally distinct, causally-independent signers* — should be one shared component in thebus, not two features.

5. **BFT's answer to echo-counting is boring and mechanical: a set keyed by signer, plus evidence carried with the claim so any reader can recount.** No cleverness. Our version is easier than theirs because GitHub already attributes and orders everything — we're being handed the hard part for free and not spending it.

6. **GitHub explicitly does not support conditional requests on unsafe methods.** This means our read-then-write guard is not fixable on the issues API — it is a property of the surface, not of our implementation. Any effort spent hardening it there is wasted.

7. **Git refs are a compare-and-swap register living inside the same repository we're already using**, with all-or-nothing multi-ref transactions. We built eventual-consistency reconciliation next to an unused linearizable primitive. That is the S3 story: the client-side workaround era ended when someone made the store consistent.

8. **Consul reaps failed nodes after 72 hours** — three days. For a membership system, tombstone retention is measured in days, not minutes. Our instinct to keep them forever is closer to correct than to paranoid.

9. **Akka's rule is that a downed node literally cannot rejoin — the process must restart to get a new UID.** The strictest production system in this set treats "rejoin after death" as *necessarily a new incarnation*. That is a strong vote for adding incarnation numbers rather than trying to make tombstones reversible.

10. **OTP's supervisor gives up after 1 restart in 5 seconds.** The oldest, most reliable supervision system in the industry is *aggressively* unwilling to restart-loop. We have no such breaker.

---

## Assumption candidates

Things worth turning into explicit, testable assumptions in thebus's canon:

- **A1.** Lease safety in thebus does not depend on any agent's local clock; only GitHub server timestamps are authoritative. *Test: grep for any agent-computed `expires_at`.*
- **A2.** `LeaseDuration > RenewDeadline > RetryPeriod × 1.2`, with renewal at ≈ L/4, and the holder ceases acting at `RenewDeadline` without needing to be told. *Test: kill an agent's network mid-turn; confirm it self-silences before the reaper fires.*
- **A3.** Lease length is derived from the measured p99 of GitHub write-visibility latency and agent turn duration, not chosen by intuition. *Test: instrument and publish the distribution; recompute L.*
- **A4.** Every work product carries the fencing token (lease-grant event number) of the seat occupancy that produced it, and any consumer rejects a product whose token is lower than the highest it has already accepted for that seat. *This is the single highest-value item in this report.*
- **A5.** Reaping is two-phase: `SUSPECT` (published, refutable, deadline scales as `log(N+1)`) → `DEAD`. A member refutes by publishing `alive` at a higher self-incremented incarnation. Only the member may raise its own incarnation.
- **A6.** After abnormal seat release, a lock-delay cooldown elapses before the seat can be re-leased.
- **A7.** Seat identity is three-level: seat / member / incarnation. A returning member always returns as a new incarnation; tombstones are never reversed, only superseded.
- **A8.** Tombstone retention exceeds the maximum staleness of any agent's roster read, and there is a compacted roster head that is the canonical read target so no reader is ever truncated past the tombstone list. *Test: the Cassandra zombie test — take an agent offline past the retention window, bring it back, see if it re-summons a retired member.*
- **A9.** A lease/reap cycle rate exceeding N-in-T for one seat escalates to a human instead of re-leasing (OTP restart intensity).
- **A10.** Quorum tallies are computed mechanically over a set keyed by `(member_id, incarnation)`, with any judgment carrying a `derived_from` edge to another member's judgment excluded from the independence count. Quorum claims embed their evidence; no agent may assert a count without the referenced items.
- **A11.** Threshold semantics are named and distinguished: "at least one independent voice" (`f+1`-style) vs. "a quorum that cannot conflict" (`n−f`-style). Strategy change requires the latter.
- **A12.** Independence requires heterogeneity: a quorum spanning only one model family is not independent, regardless of provenance edges. *No prior art — this is ours, and it is the one place the borrowed mechanisms genuinely do not cover our setting.*
- **A13.** No agent acts on a read that does not contain its own most recent write to that object (read-your-writes).
- **A14.** Every intended write has a content-derived idempotency key so retries after ambiguous failure are recognizable as the same write.
- **A15.** Mutual-exclusion decisions use a linearizable primitive (git-ref CAS or Actions concurrency group) where one is available; the issue-log tie-break is a reconciliation backstop, not the primary guard. *Prerequisite: verify GitHub's server-side CAS surface (see Inferred).*
- **A16.** Every heartbeat carries a roster digest; divergent digests are detected and trigger a re-read before the divergent agent's writes are trusted.

---

## Sources

**Leases**
- Chubby paper summary (12 s lease extension, 45 s grace period, KeepAlive held at master, sequencers, lock-delay): https://mwhittaker.github.io/papers/html/burrows2006chubby.html
- Chubby original paper (Burrows, OSDI 2006): https://static.googleusercontent.com/media/research.google.com/en//archive/chubby-osdi06.pdf
- Chubby notes — sequencer contents and lock-delay ≈ 1 minute: https://github.com/jguamie/system-design/blob/master/notes/chubby-lock-service.md
- Chubby notes — lease/grace period discussion: https://amplab.github.io/cs262a-fall2016/notes/22-Chubby.pdf
- ZooKeeper admin guide (`tickTime`, `minSessionTimeout` = 2 × tickTime, `maxSessionTimeout` = 20 × tickTime): https://zookeeper.apache.org/doc/r3.7.2/zookeeperAdmin.html
- ZooKeeper session expiry deletes ephemeral nodes: https://www.netdata.cloud/guides/zookeeper/zookeeper-session-expired/
- etcd tuning (heartbeat 100 ms, election timeout 1000 ms, ≥10 × RTT, 50 s max): https://etcd.io/docs/v3.4/tuning/
- etcd lease TTL vs election timeout, and renew-leases-after-election for clock skew: https://blog.damnever.com/en/2018/the-hole-in-etcd
- Kubernetes Leases concept (node lease in `kube-node-lease`, `spec.renewTime`, leader election, v1.36 lock-release-on-exit): https://kubernetes.io/docs/concepts/architecture/leases/
- Kubernetes node heartbeat defaults (`node-status-update-frequency` 10 s, `node-monitor-grace-period` 40 s, lease renewed at 0.25 × 40 s): https://kubernetes.io/docs/concepts/architecture/nodes/
- Node lease renew interval heuristic (0.25 × `nodeLeaseDurationSeconds`): https://github.com/kubernetes/kubernetes/pull/80173
- Kubespray Kubernetes reliability doc (grace period = (N−1) × update frequency): https://github.com/kubernetes-sigs/kubespray/blob/release-2.11/docs/kubernetes-reliability.md
- client-go leader election defaults and `LeaseDuration > RenewDeadline > RetryPeriod × JitterFactor(1.2)`: https://github.com/kubernetes/kubernetes/issues/125861
- Leader election with the Lease API (production controller design): https://getautonoma.com/blog/kubernetes-leader-election-lease-api
- Discussion of further increasing `node-monitor-grace-period`: https://github.com/kubernetes/kubernetes/issues/127352

**Fencing**
- Kleppmann, "How to do distributed locking" (fencing tokens, GC pauses, Redlock critique): https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- Same essay, PDF mirror: https://pages.cs.wisc.edu/~remzi/Classes/739/Fall2018/Papers/leases-redis-problem.pdf
- Locks, leases, fencing tokens (model-checked walkthrough): https://surfingcomplexity.blog/2025/03/03/locks-leases-fencing-tokens-fizzbee/
- Kafka zombie fencing via transactional id + producer epoch: https://blog.devgenius.io/how-kafka-applies-zombie-fencing-374b4e2f7a00
- Kafka transactions (epoch bump fences older producers): https://www.confluent.io/blog/transactions-apache-kafka/
- KIP-447 (transactional id / epoch, one active producer per id): https://cwiki.apache.org/confluence/display/KAFKA/KIP-447:+Producer+scalability+for+exactly+once+semantics
- Kafka controller epoch as split-brain fencing: https://medium.com/@aggarwalapurva89/controller-broker-a8538f44a7ba

**Tombstones**
- Cassandra tombstones (official docs): https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/tombstones.html
- `gc_grace_seconds` 864000 default, zombie resurrection, repair requirement: https://www.instaclustr.com/support/documentation/cassandra/using-cassandra/managing-tombstones-in-cassandra/
- DataStax "How is data deleted?" (grace period rationale): https://docs.datastax.com/en/cassandra-oss/3.0/cassandra/dml/dmlAboutDeletes.html
- `tombstone_warn_threshold` / `tombstone_failure_threshold`: https://digitalis.io/post/what-are-tombstones-in-cassandra-and-why-are-there-too-many
- Cassandra tombstone architecture reference: https://axonops.com/docs/data-platforms/cassandra/architecture/storage-engine/tombstones/
- CRDT tombstone growth, causal stability, tombstone-free causal CRDTs: https://blog.helsing.ai/posts/dson-a-delta-state-crdt-for-resilient-peer-to-peer-communication/
- Delta-state CRDTs by delta-mutation: https://arxiv.org/pdf/1410.2803
- Optimized conflict-free replicated set (OR-Set tombstone cost): https://arxiv.org/pdf/1210.3368
- Garbage-collected graph CRDT (practical tombstone GC): https://decomposition.al/CMPS290S-2018-09/2018/11/12/implementing-a-garbage-collected-graph-crdt-part-1-of-2.html
- CRDT survey (ACM Computing Surveys): https://dl.acm.org/doi/10.1145/3695249
- Consul/Serf failed vs left, `reconnect_timeout` 72 h, `tombstone_timeout`: https://groups.google.com/g/consul-tool/c/yEOeK4jY3Ks
- Consul `force-leave` / `-prune`: https://developer.hashicorp.com/consul/commands/force-leave
- Where is configurable reap time for client nodes (72 h default confirmed): https://github.com/hashicorp/consul/issues/6814

**Membership**
- SWIM protocol overview (SUSPECT, refutation, incarnation numbers): https://www.brianstorti.com/swim/
- SWIM incarnation numbers, self-increment only: https://apple.github.io/swift-cluster-membership/docs/current/SWIM/Enums/SWIM.html
- memberlist `config.go` (exact LAN/WAN/Local defaults, `SuspicionTimeout = SuspicionMult × log(N+1) × ProbeInterval`): https://github.com/hashicorp/memberlist/blob/master/config.go
- Lifeguard blog post (self-awareness, dogpile, buddy system, 50× false-positive reduction): https://www.hashicorp.com/en/blog/making-gossip-more-robust-with-lifeguard
- Lifeguard paper: https://arxiv.org/pdf/1707.00788
- Akka cluster membership (Address + UID, downed node cannot rejoin, unique-address rule): https://doc.akka.io/libraries/akka-core/2.6/typed/cluster-membership.html
- Akka quarantine state (UID quarantine, dead letters, requires restart): https://engineering.creditkarma.com/understanding-akkas-quarantine-state
- Akka node-not-rejoining issue (same-address auto-down behavior): https://github.com/akka/akka-core/issues/18067
- Erlang supervisor behaviour (`intensity` default 1, `period` default 5): https://www.erlang.org/doc/apps/stdlib/supervisor.html
- Erlang supervisor design principles: https://www.erlang.org/doc/system/sup_princ.html
- Erlang `global` module (registered name is an alias for a pid; replicated name tables): https://www.erlang.org/doc/apps/kernel/global.html

**Independence / double-counting**
- Bracha reliable broadcast walkthrough (ECHO/READY, `n−f`, `f+1`, quorum intersection): https://decentralizedthoughts.github.io/2020-09-19-living-with-asynchrony-brachas-reliable-broadcast/
- Bracha RBC notes (quorum intersection ≥ f+1, double-counting argument): https://hackmd.io/@alxiong/bracha-broadcast
- Practical and improved Byzantine reliable broadcast: https://eprint.iacr.org/2022/171.pdf
- BFT consensus survey (evidence/certificates): https://arxiv.org/pdf/2204.03181
- Narwhal and Tusk (certificates as transferable evidence in a DAG): https://arxiv.org/pdf/2105.11827
- Riak causal context (vector clocks, sibling explosion, dotted version vectors): https://docs.riak.com/riak/kv/2.2.3/learn/concepts/causal-context/index.html
- Riak conflict resolution: https://docs.riak.com/riak/kv/latest/developing/usage/conflict-resolution/index.html
- Dotted version vectors: https://riak.com/posts/technical/vector-clocks-revisited-part-2-dotted-version-vectors/index.html
- Dynamo paper (vector clock truncation, Merkle anti-entropy): https://docs.riak.com/riak/kv/2.2.3/learn/dynamo/index.html
- Duplicate-insensitive sketches for in-network aggregation: https://arxiv.org/pdf/0810.3227
- Synopsis diffusion (duplicate-insensitive aggregation over overlapping paths): https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/sd.pdf
- Decentralized aggregation over data streams: https://dl.acm.org/doi/pdf/10.1145/1833280.1833281

**Read-after-write**
- S3 strong read-after-write consistency announcement (1 Dec 2020): https://aws.amazon.com/about-aws/whats-new/2020/12/amazon-s3-now-delivers-strong-read-after-write-consistency-automatically-for-all-applications
- S3 consistency page: https://aws.amazon.com/s3/consistency/
- Read-your-writes consistency explained: https://arpitbhayani.me/blogs/read-your-write-consistency/
- Reading from replicas / replication lag mitigations (Box): https://medium.com/box-tech-blog/how-we-learned-to-stop-worrying-and-read-from-replicas-58cc43973638
- Replica lag pitfalls: https://incident.io/blog/dont-add-a-read-replica-until-youve-read-this
- GitHub API eventual consistency in practice (retry-after-404): https://github.com/python/the-knights-who-say-ni/issues/86
- GitHub REST best practices — ETag / If-None-Match, and conditional requests unsupported on POST/PUT/PATCH/DELETE: https://docs.github.com/rest/guides/best-practices-for-using-the-rest-api
- GitHub rate limits and conditional requests (304s free): https://github.com/orgs/community/discussions/156480
- `git update-ref` (expected old value, `--stdin` all-or-nothing transactions): https://git-scm.com/docs/git-update-ref
- `git update-ref` man page mirror: https://www.kernel.org/pub/software/scm/git/docs/git-update-ref.html
- `push --force-with-lease` as compare-and-swap: https://en.wikipedia.org/wiki/Compare-and-swap
- GitHub Actions concurrency control (`group`, `cancel-in-progress`, FIFO): https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub Actions concurrency patterns (`cancel-in-progress: false` for serialization): https://dev.to/kanta13jp1/github-actions-concurrency-patterns-cancel-in-progress-false-for-parallel-deployments-1bjm
