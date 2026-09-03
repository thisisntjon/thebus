# Agent-framework OSS survey: is member lifecycle already built?

Date: 2026-08-18
Question: does any maintained OSS multi-agent framework already implement member lifecycle
(join / leave / expire / retire), role-based routing, human approval gates, or audit trails —
and is there code to ADOPT rather than reimplement?

Method: GitHub REST API (repo metadata, contributor counts via `contributors?anon=1` Link
header, recursive git trees, file contents) + GitHub code search, run against the actual
default branches on 2026-08-18. Claims below cite the file I opened, not the README, except
where explicitly marked.

---

## What I found

### Headline

**One project is a near-miss for direct adoption: `ag2/network` in AG2 (Apache-2.0).**
It ships a hub that owns an agent registry of `Passport` / `Resume` / `Rule` records, a
capability index for addressing, an append-only `audit.jsonl`, per-channel WALs, TTL sweepers
that expire channels/tasks, "expectation" evaluators that fire on *silence* (missed ack /
missed reply / max silence) with `audit` / `notify_channel` / `auto_close` handlers, a
pluggable `HubArbiter` gatekeeper consulted before register/open/send/dispatch, and humans as
a first-class passport kind (`PassportKind = "agent" | "human" | "remote_agent"`).

It is the only surveyed project that treats *membership itself* as governed state.

But it fails thebus's two load-bearing field rules:

- **Unregister is a hard delete, not a tombstone.** `Hub.unregister` pops the passport,
  resume, rule and skill from memory and then `await self._store.delete(passport_path(...))`
  etc. Only channels and tasks survive "for audit / read". There is no retirement ledger entry
  in the identity store (the *event* is written to `audit.jsonl`, but the roster forgets).
- **Names are reusable and collision-checked, not permanent.** `register_identity` raises
  `ProtocolError("name ... already registered ... unregister it before re-registering")` —
  i.e. the design intent is explicitly "free the name by unregistering", the inverse of
  "once an agent is named the name cannot be withdrawn".
- **`last_heartbeat` exists but nothing expires a membership on it.** `AgentRuntime` carries
  `binding / target / reachable / last_heartbeat`, documented as "cache-only", refreshed by
  every frame op in `LocalLink`; `PingFrame`/`PongFrame` are "a heartbeat vocabulary" that
  `WsLink` delegates to the WebSocket library. The TTL sweeper walks *channels and tasks*, not
  memberships. So there is no seat lease — there is a liveness bit.
- **No dissent / quorum.** The only `quorum` in AG2 is the channel-invite handshake
  ("broadcasts `EV_CHANNEL_OPENED` on quorum" of invitee ACKs). No disagreement register, no
  independent-measurement requirement, no echo collapse.
- **No human *gate*.** `HumanClient` is a participant primitive ("the framework provides the
  participant primitive, not the input modality") — a human who can send and receive
  envelopes. Nothing routes a motion to a human for approval before an action commits; the
  automated `RuleBasedArbiter` is the only gatekeeper.

**Second: Temporal already has the seat-lease/retirement semantics you want — at the worker
layer, in a server you would run, not a library you would vendor.** `WorkerHeartbeat`
(instance_key namespace-unique, worker_identity non-unique, status, start_time,
heartbeat_time, elapsed_since_last_heartbeat, deployment_version) plus `ListWorkers` /
`DescribeWorker`, plus `VersionDrainageStatus` (`DRAINING` → `DRAINED` → safe to
decommission) and `DeploymentReachability` (`REACHABLE` → `CLOSED_WORKFLOWS_ONLY` →
`UNREACHABLE`). That last enum is the closest thing in OSS to TOMBSTONE-with-safety: you may
not decommission a version while work can still route to it. Task queues are the role-based
addressing (work goes to a queue name; workers poll it; no worker is ever addressed by name).
Event history is the durable audit trail.

**Everything else: no member lifecycle.** The frameworks model *tasks*, *sessions*, *graph
runs* and *tool calls* as the governed objects. Agents are objects you construct in code, a
row in a config, or a Kubernetes Deployment. Nobody joins, nobody leases, nobody retires.

### Per-candidate assessment

Legend for (a) member lifecycle w/ expiry or heartbeat, (b) role-based addressing vs direct
naming, (c) human approval gate, (d) durable audit trail, (e) disagreement handling.

| Project | License | Stars | Contribs | Last push | a | b | c | d | e |
|---|---|---|---|---|---|---|---|---|---|
| ag2ai/ag2 (`ag2/network`) | Apache-2.0 | 4,872 | 501 | 2026-08-18 | partial | yes (capability index) | no | yes (audit.jsonl + WAL) | no |
| temporalio/temporal + /api | MIT | 22,389 | — | 2026-08-18 | **yes** | yes (task queues) | no | **yes** (event history) | no |
| agentscope-ai/agentscope | Apache-2.0 | 29,029 | 97 | 2026-08-14 | infra only (TTL locks) | no | partial (parked runs) | partial | no |
| langchain-ai/langgraph (+langchain) | MIT | 39,947 | 284 | 2026-08-18 | no | no | **yes** (interrupt) | yes (checkpointer) | no |
| openai/openai-agents-python | MIT | 28,752 | 354 | 2026-08-18 | no | no (handoffs by agent) | yes (`needs_approval`) | partial (tracing) | no |
| microsoft/agent-framework | MIT | 12,873 | 205 | 2026-08-18 | no | no | yes (tool approval, RequestInfo) | yes (checkpoint store) | no |
| microsoft/autogen (core) | CC-BY-4.0 | 60,499 | — | 2026-04-15 **maintenance mode** | no | **yes** (`AgentId(type,key)` + subscriptions) | no | no | no |
| crewAIInc/crewAI | MIT | 57,267 | 303 | 2026-08-18 | no | weak (role string lookup) | yes (in-loop feedback) | no | no |
| kagent-dev/kagent | Apache-2.0 | 3,538 | 176 | 2026-08-18 | k8s pod-level | via A2A/CRD | no | k8s events | no |
| google/adk-python | Apache-2.0 | 21,172 | 449 | 2026-08-18 | no | no | not found | sessions | no |
| a2aproject/A2A | Apache-2.0 | 25,400 | 157 | 2026-08-18 | no (`heartbeat`: 0 hits) | AgentCard discovery | `input-required` task state | no | no |
| agntcy/dir | Apache-2.0 | 175 | 35 | 2026-08-18 | no | naming + routing/peer | no | signed records | no |
| camel-ai/camel | Apache-2.0 | 17,603 | 232 | 2026-08-14 | dynamic worker creation only | workforce roles | no | no | no |
| OpenHands/OpenHands | MIT | 84,420 | 520 | 2026-08-18 | no | no | confirmation mode | event stream | no |
| 2FastLabs/agent-squad | Apache-2.0 | 7,739 | 37 | 2026-08-15 | no | classifier routing | no | storage of conversations | no |
| mastra-ai/mastra | NOASSERTION | 27,281 | 646 | 2026-08-18 | no | no | suspend/resume steps | workflow snapshots | no |
| Significant-Gravitas/AutoGPT | NOASSERTION | 186,672 | — | 2026-08-18 | no | no | graph-level | execution records | no |
| langgenius/dify | NOASSERTION | 152,836 | — | 2026-08-18 | no | no | workflow node | workspace logs | no |

Dead / superseded / moved — do not build on:

- **microsoft/autogen** — README carries a `Maintenance Mode` badge and a CAUTION block:
  "AutoGen is now in maintenance mode… New users should start with Microsoft Agent Framework."
  Last push 2026-04-15.
- **microsoft/semantic-kernel** — README line 4: "Semantic Kernel is now Microsoft Agent
  Framework!… the enterprise-ready successor". Repo still receives commits but is a migration
  target.
- **letta-ai/letta** — as of commit `chore: archive the legacy server repository (#3430)`
  (2026-08-16) the repo is **a landing page**: 11 files, no source. "The retired Letta V1
  server source is preserved on the `archive` branch." Code moved to `letta-ai/letta-code`
  (Apache-2.0, 3,042★). The persistent-agent-registry-in-Postgres that made Letta the closest
  thing to an agent roster is no longer the shipped product.
- **FlowiseAI/Flowise** — `archived: true`.
- **TransformerOptimus/SuperAGI** — last push 2025-01-22. Dead.
- **FoundationAgents/MetaGPT** — last push 2026-01-21. ~7 months idle.
- **openai/swarm** — last push 2026-04-15; educational, superseded by the Agents SDK.
- **awslabs/agent-squad** — the repo now redirects to **2FastLabs/agent-squad**; its README
  says "previously hosted at `awslabs/agent-squad`… now maintained at `2fastlabs/agent-squad`".
  AWS handed the project off.
- **inngest/agent-kit** — 920★, last push 2026-04-29, ~4 months idle.

### What each capability actually looks like in the wild

**(a) Member lifecycle.** Only three implementations exist and none is a seat lease over named
members:
1. AG2 hub registry (register / unregister / set_resume / record_observation), no expiry.
2. Temporal `WorkerHeartbeat` + deployment drainage — a real heartbeat-and-retire model, but
   the "member" is a *worker process*, identity is `instance_key`, and the roster is
   server-side state you query, not a ledger you carry.
3. AgentScope's `app` layer, which has genuine lease primitives —
   `MessageBus.acquire_lock(key, ttl_secs=600)` documented as "typically with a heartbeat task
   that renews the TTL so the lease only expires if the holding process dies",
   `try_lock` / `unlock`, and `registry_set(namespace, field, ttl_secs)` — but they lease
   *documents, sessions and channel-forwarding rights*, not memberships
   (`tests/index_worker_lease_test.py`, `_index_worker.py`: "acquires the processing lease via
   storage CAS so only one worker in the cluster handles the document at a time").

Everywhere else `heartbeat` returns **0 hits**: crewAI, letta, google/adk-python, a2aproject/A2A,
kagent. In langgraph the 8 hits are Docker/retry unrelated. In microsoft/agent-framework the
single hit is an `AGENTS.md`.

**(b) Role-based addressing.** The best prior art is AutoGen core's `AgentId(type, key)`:
"Agent ID uniquely identifies an agent instance within an agent runtime… It is the 'address'
of the agent instance", where `type` "associates an agent with a specific factory function"
and instances are created lazily per key; `TypeSubscription(topic_type, agent_type)` routes a
topic to an agent type and uses the topic *source* as the instance key. That is structurally
"route to a seat, let the runtime bind an occupant" — and it is in the repo Microsoft put into
maintenance mode. AG2's capability index (`_capability_index[cap] -> {agent_id}`, populated
from `resume.claimed_capabilities` and `resume.observed`) is the live equivalent. CrewAI is
the weak case: `role` is a persona prompt string that doubles as a lookup key
(`agt.role == task_config["agent"]`, `agent_id=str(agent.role)`), with no registry behind it.
Everyone else (OpenAI Agents SDK handoffs, adk-python sub-agents, agent-squad classifiers)
addresses a concrete agent object.

**(c) Human gates.** These are mature — for *tool calls*, not for *motions*.
- LangChain/LangGraph `HumanInTheLoopMiddleware` wraps tool calls in `interrupt()` with
  `DecisionType = "approve" | "edit" | "reject" | "respond"`, durable because the checkpointer
  persists the interrupted state and `Command(resume=...)` resumes it. This is the best
  general-purpose HITL implementation in OSS.
- OpenAI Agents SDK: `needs_approval` (bool or callable/awaitable) evaluated per tool call
  (`src/agents/util/_approvals.py`).
- Microsoft Agent Framework: `_harness/_tool_approval.py`, `_workflows/_request_info_mixin.py`
  (workflow pauses and emits a request for external input), plus checkpointing.
- CrewAI: `HumanInputProvider` protocol, an in-executor feedback loop ("prompt user, loop until
  satisfied").
- AgentScope: parked runs — `WAKEUP_KIND_RESUME` is "resume a session parked on an awaiting
  tool call by feeding it a human-in-the-loop result", and it projects "a team member's pending
  HITL request onto its leader" via a per-session projection registry.

None of these is "agents file motions, only humans act" as a *fleet-level* rule; all are
"this tool call pauses until someone answers".

**(d) Durable audit trail.** LangGraph checkpointers, Temporal event history, AG2
`audit.jsonl` + per-channel WAL, Agent Framework `ICheckpointStore` / `FileSystemJsonCheckpointStore`.
AG2's audit log is the only one whose record kinds are *governance* kinds: register,
unregister, set_resume (with `source: "tenant" | "observed"`), set_skill, set_rule, channel
created/closed/expired, task terminated, expectation violations, notify-handler crashes — and
the kind set is explicitly open for tenant extension. None of them is hash-chained or
tamper-evident.

**(e) Disagreement.** Nothing. `quorum` = 0 hits in langgraph, camel, crewAI and
microsoft/agent-framework; 2 hits in AG2 and both are the invite-ACK handshake. `dissent` = 0
real hits anywhere (the two AutoGen hits are prompt text in Anthropic caching samples).
`tombstone` = 1 hit in agent-framework (an unrelated approval-lifecycle test) and 1 in
langgraph (an examples README). The multi-agent literature's "debate" patterns are prompt
techniques, not registers.

### Adjacent (non-framework) projects that overlap thebus directly

- **chanceryhq/chancery** (Apache-2.0, 25★, Go, 51 commits, **1 contributor**, last push
  2026-07-21): capability grants to agents with `--ttl 8h`, revocation, "short-lived leases a
  cooperating server verifies", and a hash-chained tamper-evident audit log
  (`chancery audit verify`). Closest OSS implementation of expiring-lease + provenance-audit
  mechanics as a standalone tool. Bus factor 1 — read it, don't depend on it.
- **digitaldrywood/detent** (MIT, 13★): a Go binary that watches a board / GitHub issues and
  runs "retries, leases, and gates", with an explicit `Human Review` lane and
  `AUTO_PROMOTE_ENABLED=false`. Independent reinvention of the same idea at toy scale.
- **wotai-dev/woterclip** (MIT, 57★): GitHub Issues → `/heartbeat` → persona matching → work →
  report back, with "the human is the Board – the ultimate escalation target". Uses the word
  heartbeat for the *poll loop*, not for member liveness.
- **Getty/karr** (8★, **no license file** → unusable): "Kanban Assignment & Responsibility
  Registry — git-native, file-based kanban for shared helper agents", with per-repo locks and
  `KARR_ROLE`.
- **agntcy/dir** (Apache-2.0, 175★, 35 contributors): a content-addressed *directory* of signed
  agent records — naming + name verification, routing/peer, runtime workload discovery, sign
  service. Registry-with-provenance shaped, but records describe published agent artifacts;
  there is no membership, no expiry, no gate.
- **davccavalcante/krikos** — description is a literal match ("Identity registry and lifecycle
  management for fleets of AI agents") but the repo has **1 commit, 1 contributor**. Ignore.

The GitHub-issues-as-agent-bus pattern is being reinvented constantly (woterclip, detent,
polyphony, baton, shipwright, better-symphony, slashbin-ai-foreman, ai-scrum-master-template —
all MIT, all 12–60★, all created in the last ~6 months, all single-maintainer). None of them
has membership, dissent, or echo collapse. This is corroborating evidence that the transport
choice is obvious and the governance layer is the unbuilt part.

---

## Verified vs inferred

**Verified by opening code or repo metadata on 2026-08-18:**
- All stars / licenses / last-push dates / archived flags / contributor counts in the table
  (GitHub REST `repos/{r}`, `repos/{r}/contributors?anon=1`).
- AutoGen maintenance-mode banner; Semantic Kernel successor banner; Flowise archived; Letta
  reduced to 11 files with the archive note; agent-squad's move from awslabs to 2FastLabs.
- AG2: hub docstring (registry / WAL / audit log / sweepers), `Passport`/`Resume`/`AgentRuntime`
  fields, `register_identity` name-collision rejection, `unregister` deleting identity files,
  `audit.py` record kinds, `expectations.py` evaluators and handlers, `arbiter.py` Allow/Deny,
  `human_client.py` scope, `frames.py`/`local.py` heartbeat semantics, 50 test files under
  `test/network/` including `test_audit_and_lifecycle.py` and `test_client_lifecycle.py`,
  releases v1.0.0 (2026-07-27) → v1.0.2 (2026-08-15).
- Temporal: `WorkerHeartbeat` message fields, `VersionDrainageStatus`, `DeploymentReachability`.
- AgentScope: `MessageBus.acquire_lock/try_lock/registry_set` TTL semantics, channel heartbeat
  TTL in `_dispatcher.py`, `WAKEUP_KIND_RESUME`, subagent-HITL projection.
- LangChain `HumanInTheLoopMiddleware` decision types; LangGraph `interrupt` / `Command(resume=)`.
- OpenAI Agents SDK `_approvals.py`; AutoGen `AgentId` / `TypeSubscription`; CrewAI
  `HumanInputProvider` and role-string lookups in `crew.py`; kagent CRD shapes.
- Zero-hit code searches for `heartbeat`, `quorum`, `dissent`, `tombstone` in the repos named.

**Inferred (not directly verified):**
- adk-python, Dify, AutoGPT, ChatDev, Mastra and OpenHands were assessed from repo metadata,
  tree structure and one or two searches each, not a full read. Their "no" on (a) and (e) is
  high-confidence (nothing in the trees or searches suggests otherwise); their (c)/(d) grades
  are approximate.
- I did not audit AG2's `ag2/network/views`, `rule.py` or `auth.py` in depth; the Rule/access
  model may contain more gating than I credit.
- Temporal's worker-heartbeat API is server-side and its SDK-side emission was not read.
- Absence of a term in GitHub code search is strong but not absolute evidence (indexing lag,
  tokenization). "lease" specifically is unreliable as a search term — it matches "release".

---

## Surprises

1. **AG2 quietly shipped a governance layer.** AG2 is usually written off as "the AutoGen 0.2
   fork". Its v1.0 (2026-07-27) removed the classic framework and promoted `autogen.beta`,
   which contains `ag2/network`: passports, resumes, capability routing, WAL, arbiter,
   expectations, audit log. This is the single most thebus-shaped code in OSS and it is almost
   invisible in the discourse (4,872 stars vs AutoGen's 60k).
2. **Letta stopped being open in the way that mattered.** Two days before this survey
   (2026-08-16) the Letta V1 server was archived; `letta-ai/letta` is now a landing page. The
   canonical "agents are durable database rows you can list" implementation left the building.
3. **AWS abandoned agent-squad** — `awslabs/agent-squad` now redirects to a third-party org.
4. **The two biggest Microsoft frameworks both self-deprecated** in favor of
   `microsoft/agent-framework`, which is itself only 12.9k stars — the consolidation is real
   and recent, and neither AutoGen's `AgentId` type-addressing nor anything like it survived
   the merge in an obvious form.
5. **Retirement-with-safety exists, but only in Temporal**, expressed as
   `DEPLOYMENT_REACHABILITY_{REACHABLE,CLOSED_WORKFLOWS_ONLY,UNREACHABLE}` — "the deployment
   cannot be decommissioned safely" is exactly thebus's argument for why deletion is the wrong
   primitive, written by a workflow-engine team for entirely different reasons.
6. **Disagreement is a total void.** Twenty-plus maintained frameworks, hundreds of thousands
   of stars, and not one `quorum`, `dissent`, or dissent-register construct. The two field
   rules thebus is built on (names can't be withdrawn; one member's doom-conclusion spreads)
   have no counterpart anywhere.

---

## Assumption candidates

Things to treat as load-bearing assumptions to re-test, not settled facts:

1. **"Member lifecycle is unbuilt" is now ~85% confident, not 100%.** AG2's `ag2/network` is
   close enough that thebus should be re-justified *against it specifically*, in writing. If
   AG2 adds membership TTL and a tombstoned unregister, the overlap becomes uncomfortable.
2. **Adopt-vs-reimplement candidates, in order:**
   - *Vendor the record shapes, not the runtime*: AG2's `Passport` / `Resume` / `Rule` split
     (immutable identity vs mutating capability claims vs access policy) and its open-kind
     `audit.jsonl` convention are directly liftable as a schema, Apache-2.0, ~1 file each.
   - *Copy Temporal's enum semantics*: model retirement as
     `ACTIVE → DRAINING → DRAINED → DECOMMISSIONED` with an explicit reachability predicate,
     rather than as a delete + tombstone row. It is battle-tested vocabulary and it makes the
     "can we retire this seat yet?" question decidable.
   - *If thebus ever needs a durable gate*: LangGraph's `interrupt` + checkpointer is the
     best-maintained HITL implementation and is MIT — but adopting it means adopting LangGraph
     as the execution substrate, which is a much bigger commitment than the gate is worth.
   - *If the lease ever needs to be real (not GitHub-issue-shaped)*: AgentScope's
     `acquire_lock(ttl) + heartbeat renewal` pattern, or plain etcd/Consul TTL leases, are the
     correct references. Do not invent lease renewal semantics.
3. **Do not adopt any of the small governance-adjacent projects** (chancery, detent, krikos,
   karr). Every one is bus-factor 1 and under six months old. Read chancery's hash-chained
   audit design; don't depend on the code.
4. **Assumption to watch:** that A2A / agntcy-style *directories* stay out of membership.
   Both are heading toward "registry of agents" and either could grow expiry and revocation.
   A2A in particular has the ecosystem weight (25.4k stars, Linux Foundation) to make its
   AgentCard the de-facto identity record, at which point thebus's passport should probably
   be an AgentCard extension rather than a new schema.
5. **Unverified claim worth checking before publishing anything comparative:** whether
   `microsoft/agent-framework` has an agent *catalog/registry* surface I missed. I found
   `WorkflowCatalog.cs` and a family of `AgentSessionStore` implementations, which suggests
   session/thread persistence rather than a roster, but the .NET side is 6,000+ files and I
   sampled it.

---

## Sources

Repo metadata (license / stars / contributors / last push / archived) fetched 2026-08-18 via
`gh api repos/{owner}/{repo}` and `gh api repos/{owner}/{repo}/contributors?per_page=1&anon=1`
(Link header `rel="last"`).

AG2:
- https://github.com/ag2ai/ag2/blob/main/ag2/network/hub/core.py (module docstring: registry /
  WAL / audit log / sweepers; `register_identity` name-collision `ProtocolError`; `unregister`
  deleting `passport_path` / `resume_path` / `rule_path` / `skill_path`; capability index)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/identity.py (`Passport`, `Resume`,
  `AgentRuntime.last_heartbeat`, `PassportKind`)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/hub/audit.py (audit record kinds, open kind set)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/hub/expectations.py (`acks_within`,
  `reply_within`, `max_silence`; `audit` / `notify_channel` / `auto_close`)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/hub/arbiter.py (`HubArbiter`, `Allow`/`Deny`)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/hub/sweepers.py (`_IntervalSweeper`)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/client/human_client.py
- https://github.com/ag2ai/ag2/blob/main/ag2/network/transport/frames.py (Ping/Pong heartbeat vocabulary)
- https://github.com/ag2ai/ag2/blob/main/ag2/network/transport/local.py ("every frame operation
  refreshes `last_heartbeat`")
- https://github.com/ag2ai/ag2/tree/main/test/network (50 files incl. `test_audit_and_lifecycle.py`,
  `test_client_lifecycle.py`, `test_control_plane.py`)
- Releases v1.0.0 2026-07-27, v1.0.2 2026-08-15; first commit at path `ag2/network`:
  `feat!: promote autogen.beta to autogen, remove classic framework (#3023)` 2026-06-27
- https://github.com/ag2ai/ag2/blob/main/website/docs/_blogs/2026-05-16-AG2-Network-What-Survives/index.mdx
  (design-intent post; not read in full)

Temporal:
- https://github.com/temporalio/api/blob/main/temporal/api/worker/v1/message.proto
  (`WorkerHeartbeat`: instance_key, worker_identity, host_info, deployment_version, status,
  start_time, heartbeat_time, elapsed_since_last_heartbeat; `WorkerInfo`, `WorkerListInfo`,
  `WorkerCommand`)
- https://github.com/temporalio/api/blob/main/temporal/api/enums/v1/deployment.proto
  (`DeploymentReachability`, `VersionDrainageStatus`, `WorkerVersioningMode`,
  `WorkerDeploymentVersionStatus`)
- https://github.com/temporalio/api/blob/main/temporal/api/workflowservice/v1/service.proto
  (ListWorkers / DescribeWorker / worker-deployment RPCs — located via code search, not read)

AgentScope:
- https://github.com/agentscope-ai/agentscope/blob/main/src/agentscope/app/message_bus/_base.py
  (`acquire_lock(ttl_secs=600)` "typically with a heartbeat task that renews the TTL",
  `try_lock`, `unlock`, `registry_set(..., ttl_secs)`, `registry_getall`, `session_run` TTL)
- https://github.com/agentscope-ai/agentscope/blob/main/src/agentscope/app/message_bus/_keys.py
  (`WAKEUP_KIND_WAKE` / `_RESUME` / `_MESSAGE`; subagent HITL projection onto leader)
- https://github.com/agentscope-ai/agentscope/blob/main/src/agentscope/app/channel/_dispatcher.py
  ("TTL of a node's per-channel status heartbeat", `channel_forward_lease`)
- https://github.com/agentscope-ai/agentscope/blob/main/src/agentscope/app/_service/_index_worker.py
  (storage-CAS processing lease)
- https://github.com/agentscope-ai/agentscope/blob/main/tests/index_worker_lease_test.py

LangChain / LangGraph:
- https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/types.py
  (`class Interrupt`, `interrupt()`, `Command(resume=...)`)
- https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/middleware/human_in_the_loop.py
  (`DecisionType = "approve" | "edit" | "reject" | "respond"`, `ReviewConfig`)

OpenAI:
- https://github.com/openai/openai-agents-python/blob/main/src/agents/util/_approvals.py
  (`evaluate_needs_approval_setting`)
- https://github.com/openai/openai-agents-python/tree/main/src/agents/handoffs
- https://github.com/openai/swarm (last push 2026-04-15)

Microsoft:
- https://github.com/microsoft/autogen (README maintenance-mode CAUTION block)
- https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/_agent_id.py
  (`AgentId(type, key)`)
- https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/_type_subscription.py
- https://github.com/microsoft/semantic-kernel (README successor banner)
- https://github.com/microsoft/agent-framework — trees:
  `python/packages/core/agent_framework/_harness/_tool_approval.py`,
  `python/packages/core/agent_framework/_workflows/_request_info_mixin.py`,
  `python/packages/core/agent_framework/_workflows/_checkpoint.py`,
  `dotnet/src/Microsoft.Agents.AI.Workflows/Checkpointing/*`,
  `dotnet/src/Microsoft.Agents.AI.Hosting/*AgentSessionStore.cs`, `WorkflowCatalog.cs`

CrewAI:
- https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/core/providers/human_input.py
- https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/crew.py
  (`agt.role == task_config["agent"]`, `agent_id=str(agent.role)`, `task.human_input = True`,
  `manager_agent`)

Letta:
- https://github.com/letta-ai/letta (README landing-page note; commit
  `chore: archive the legacy server repository (#3430)` 2026-08-16; tree = 11 paths)
- https://github.com/letta-ai/letta-code (Apache-2.0, 3,042★)

Others:
- https://github.com/kagent-dev/kagent/blob/main/go/api/v1alpha2/agent_types.go
  (`AgentSpec`, `DeclarativeDeploymentSpec`, `BYOAgentSpec`, `SharedDeploymentSpec.Replicas`);
  CRDs under `go/api/config/crd/bases/kagent.dev_{agents,agentharnesses,sandboxagents}.yaml`
- https://github.com/a2aproject/A2A/blob/main/specification/a2a.proto (AgentCard; `heartbeat` 0 hits)
- https://github.com/agntcy/dir/blob/main/proto/agntcy/dir/runtime/v1/workload.proto
- https://github.com/agntcy/dir/blob/main/proto/agntcy/dir/naming/v1/naming_service.proto
- https://github.com/2FastLabs/agent-squad (README "New home… previously hosted at awslabs/agent-squad")
- https://github.com/FlowiseAI/Flowise (archived: true)
- https://github.com/TransformerOptimus/SuperAGI (last push 2025-01-22)
- https://github.com/FoundationAgents/MetaGPT (last push 2026-01-21)
- https://github.com/camel-ai/camel/blob/master/camel/societies/workforce/workforce.py
  (`create_worker_node_for_task`)
- https://github.com/OpenHands/OpenHands (confirmation-mode settings surfaces)
- https://github.com/chanceryhq/chancery (README: `--ttl 8h` grants, `chancery audit verify`;
  51 commits, 1 contributor)
- https://github.com/digitaldrywood/detent (README: "retries, leases, and gates", `Human Review`)
- https://github.com/wotai-dev/woterclip (README: `/heartbeat` loop, "the human is the Board")
- https://github.com/Getty/karr (no LICENSE file)
- https://github.com/davccavalcante/krikos (1 commit)

Negative-result code searches (all run 2026-08-18, `gh api search/code`):
`heartbeat repo:crewAIInc/crewAI` = 0; `heartbeat repo:letta-ai/letta` = 0;
`heartbeat repo:google/adk-python` = 0; `heartbeat repo:a2aproject/A2A` = 0;
`heartbeat repo:kagent-dev/kagent` = 0; `heartbeat repo:microsoft/agent-framework` = 1 (AGENTS.md);
`quorum` = 0 in langgraph / camel / crewAI / microsoft/agent-framework, = 2 in ag2 (invite ACK);
`dissent` = 0 real hits; `tombstone` = 1 unrelated hit each in agent-framework and langgraph.
