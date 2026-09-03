# Interop Standards vs. thebus Primitives — Primary-Source Audit

**Date:** 2026-08-18
**Question:** Are voting and dissent preservation actually absent from agent interop protocols, and can A2A carry thebus primitives as extensions?
**Method:** Read the actual specifications (A2A v1.0/v1.0.1, MCP 2026-07-28, ACP, ANP, ERC-8004). The Kang & Diponegoro paper (arXiv 2606.31498) was read *last*, as a claim to be tested, not a source.

---

## What I found

### Headline

**The paper's central claim survives contact with the primary specs.** Voting and dissent preservation are genuinely absent — not "underspecified," but not present as concepts — in every spec I read. In one case (ANP) the spec says so in its own words. But **two of the paper's cell-level ratings are wrong or indefensible**, and its most load-bearing claim *in our favour* — that A2A extensions can add RPC methods and state machines — is **half true in a way that matters to our design**.

### 1. A2A (v1.0 released 2026-03-12; v1.0.1 patch 2026-05-28, Linux Foundation)

**Task state machine — fully specified, 8 states + unspecified.**
`TASK_STATE_SUBMITTED`, `WORKING`, `COMPLETED`, `FAILED`, `CANCELED`, `REJECTED`, `INPUT_REQUIRED`, `AUTH_REQUIRED` (+ `TASK_STATE_UNSPECIFIED`). Terminal: COMPLETED / FAILED / CANCELED / REJECTED — "a task reaches a terminal state … it cannot restart." Interrupted (resumable): INPUT_REQUIRED / AUTH_REQUIRED.

There is a **rejection** state — an agent "decided to not perform the task." That is the closest thing in any spec to an agent registering an objection. It is not a dissent: it is per-task, bilateral, terminal, and carries no obligation to preserve or attribute the reasoning to anything outside that task.

**Agent lifecycle / membership — absent, and the spec says so.**
Discovery is: `.well-known/agent-card.json`, curated registries, or direct config. On registries the spec states outright that **"the current A2A specification does not prescribe a standard API for curated registries."** There is no register/deregister call, no TTL, no expiry field on the Agent Card, no retirement or unavailability semantics. **Our SEAT LEASE and TOMBSTONE have no counterpart and no hook to attach to.**

**Voting / dissent / quorum / consensus / deliberation — absent.** Targeted term search across `docs/specification.md` for *lease, deregister, retire, revoke, vote, quorum, dissent, objection, consensus, membership, escalation* returned no hits.

**Human escalation — present, and better than the paper credits.** `INPUT_REQUIRED` ("the agent should respond with an `input-required` task state to request clarification") and `AUTH_REQUIRED` (agent "delegate[s] the fulfillment of this authorization to the client") are exactly a human gate at the task level. What is missing is *governance* escalation — a motion filed against the fleet rather than a question asked inside one task. The paper's "Absent" is defensible only under its own narrower definition; on a plain reading it is wrong. See Surprises.

**Audit — present in meaningful part.** `Task.history` (array of Messages), `historyLength` parameter on retrieval, `contextId` that "logically groups multiple related Task and Message objects, providing continuity across a series of interactions," a **`tasks/list` method with filtering and pagination added in v1.0**, push-notification webhooks, and JWS-signed Agent Cards (RFC 7515 + RFC 8785 canonicalization). Caveats the spec itself flags: "The agent is responsible to determine which Messages are persisted," and streaming "MUST NOT be considered a reliable delivery mechanism."

**The extension mechanism — THE key finding, and it is more constrained than the paper says.**

There are two documents and they do not agree in scope.

*Non-normative guide* (`docs/topics/extensions.md`) names four foreseeable categories:
- Data-only: "Exposing new, structured information in the Agent Card that doesn't impact the request-response flow."
- Profile: "Overlaying additional structure and state change requirements on the core request-response messages."
- Method Extensions (Extended Skills): **"Adding entirely new RPC methods beyond the core set defined by the protocol."**
- State Machine: **"Adding new states or transitions to the task state machine."**

*Normative specification* §4.6.2 names only **two** extension points: **Message Extensions** and **Artifact Extensions**. The phrases "RPC method" and "state machine" do not appear anywhere in §4.6.

*And the guide contradicts itself.* Its limitations section forbids:
- **"Changing the Definition of Core Data Structures"** — no adding/removing fields on protocol-defined structures; custom attributes go in `metadata` maps.
- **"Adding New Values to Enum Types"** — "Extensions should use existing enum values and annotate additional semantic meaning in the `metadata` field."

So "State Machine Extensions" cannot mean a new `TaskState` enum member. It means: reuse an existing state and carry the real semantics in `metadata`. Plus: "An extension MUST NOT provide a way to bypass the agent's primary security controls," and extension methods "MUST ensure these methods are subject to the same authentication and authorization checks as the core A2A methods."

**Mechanics.** Declared as `AgentExtension` objects (`uri`, `description`, `required`, `params`) inside `AgentCapabilities.extensions` on the Agent Card. Activated per-request via the **`A2A-Extensions` HTTP header** — comma-separated URIs; the agent echoes back successfully activated ones in the response header. **Note: the header is `A2A-Extensions`, not `X-A2A-Extensions`.** If `required: true` and the client does not activate, the agent MUST return `ExtensionSupportRequiredError`. Versioning is by URI: "A new URI MUST be created for breaking changes."

**Extension governance is real and has a cost.** Two tiers under `a2aproject`: `experimental-ext-{name}` (needs an A2A Maintainer sponsor) and `ext-{name}` (official; needs Apache 2.0 + at least one reference implementation; graduation requires a **TSC vote at 50% quorum with majority approval**). Official URIs live under `https://a2a-protocol.org/extensions/{name}/v1`. Named extensions I could identify: Secure Passport, Timestamp/Hello World, Traceability, Agent Gateway Protocol (AGP). **No governance, voting, dissent, membership, or lease extension exists** in either tier.

### 2. MCP (latest spec revision 2026-07-28)

MCP is not an agent protocol and does not pretend to be. Its own scope statement: "an open protocol that enables seamless integration between LLM applications and external data sources and tools." Participants are **Hosts / Clients / Servers** — no peers, no agents-as-members. Features: Resources, Prompts, Tools (server→client); Elicitation (client→server). The 2026-07-28 revision moved to "Stateless, self-contained requests" with "Per-request capability negotiation," and Sampling/Roots no longer appear in the top-level client-feature list.

Membership, agent registry, agent-to-agent messaging, voting, dissent, quorum: **none of it exists, at any level.** Human-in-the-loop is present only as *principles* ("Users must explicitly consent to and understand all data access and operations") which the spec admits it cannot enforce: "While MCP itself cannot enforce these security principles at the protocol level, implementors SHOULD…". Audit is weaker than A2A's, not stronger.

MCP does have its own extension mechanism (identifiers `{vendor-prefix}/{extension-name}`, SEP Extensions Track, negotiated via `_meta` capability blocks). Current official extensions: OAuth Client Credentials, Enterprise-Managed Authorization, MCP Apps, MCP Tasks. **Nothing agent-, identity-, membership-, or governance-related.**

**Verdict: MCP is structurally the wrong layer. Not a gap to fill — a category difference.** Do not model thebus on MCP.

### 3. ACP

**ACP has been absorbed.** Its own site states "ACP is now part of A2A under the Linux Foundation," with a migration guide. It contributed REST-based communication, async-first with sync support, MIME-typed multimodality, streaming, stateful/stateless modes, and "Offline Discovery" (metadata embedded in distribution packages so inactive agents remain discoverable). No deregistration, voting, dissent, or deliberation.

**Consequence: ACP is not a live alternative target.** The paper treats it as one of five standing protocols; as of Aug 2026 that is stale. Reading it as a fifth independent data point overstates the breadth of the survey.

### 4. ANP

ANP anchors every agent to a DID (`did:wba:…`) with a web-resolvable DID document, and describes agents via Agent Description Protocol (JSON-LD). Its meta-protocol is **bilateral only**: "a caller and a target agent select the protocol, interface, Profile, schema, content type, security profile, and execution mode." The target decides unilaterally from "local policy, authorization state, and caller capabilities."

**ANP explicitly disclaims governance in its own non-goals:** *"This specification does not define: … A global protocol registry, consensus-protocol election algorithm, or economic incentive mechanism."* And in future work: *"Future versions may define: … Protocol consensus, voting, review, and governance mechanisms."*

This is the single strongest primary-source confirmation of the paper's thesis, and it is a self-report — the spec authors agree the gap is real and unfilled.

### 5. ERC-8004 ("Trustless Agents")

Three registries on any L2 or mainnet.

- **Identity Registry** — ERC-721 + URIStorage. `register(string agentURI, MetadataEntry[] metadata) → uint256 agentId`, `setAgentURI`, `setAgentWallet(agentId, newWallet, deadline, signature)`, `unsetAgentWallet`, `getMetadata`/`setMetadata`. Agent identity = `{namespace}:{chainId}:{identityRegistry}` + agentId.
- **Reputation Registry** — `giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals, string tag1, string tag2, string endpoint, string feedbackURI, bytes32 feedbackHash)`, `revokeFeedback(agentId, feedbackIndex)`, `appendResponse(agentId, clientAddress, feedbackIndex, responseURI, responseHash)`, `readAllFeedback(..., bool includeRevoked)`, `getSummary(...)`.
- **Validation Registry** — `validationRequest`, `validationResponse(bytes32 requestHash, uint8 response, …)`, `getValidationStatus`, `getAgentValidations`, `getValidatorRequests`.

**No deregistration, retirement, or revocation of an agent.** Once registered, agents persist on-chain. The owner can transfer the NFT, `unsetAgentWallet()`, or flag status in metadata — all workarounds, none normative retirement. **ERC-8004 does not solve our TOMBSTONE.**

**But it comes closer to a DISSENT REGISTER than the paper allows.** `giveFeedback` takes a **signed** `int128` — negative judgments are first-class and explicitly exemplified (`tradingYield` of `-3.2%` as value `-32`, `valueDecimals: 1`). Feedback is attributed to `msg.sender`. `revokeFeedback` **sets an `isRevoked` flag but preserves the record**, and `readAllFeedback` exposes `includeRevoked` — that is *exactly* our "retirement is a ledger entry, never a deletion" pattern, and *exactly* our "preserved but quarantined from orientation" pattern. `appendResponse` gives the subject a reply that does not overwrite the original. The spec states: **"On-chain pointers and hashes cannot be deleted, ensuring audit trail integrity."**

No voting or quorum. The spec deliberately punts: "more complex reputation aggregation will happen off-chain" via "specialized services for agent scoring, auditor networks."

### 6. Agent Cards vs. our harness capability profiles

`AgentCard`: `name`, `description`, `supportedInterfaces` (each with `protocolVersion`), `provider`, `iconUrl`, `version`, `documentationUrl`, `capabilities` (`streaming`, `pushNotifications`, `extendedAgentCard`, `extensions`), `defaultInputModes`, `defaultOutputModes`, `securitySchemes`, `security`, `skills`, `signature`.
`AgentSkill`: `id`, `name`, `description`, `tags`, `examples`, `inputModes`, `outputModes`.
Served at `https://{domain}/.well-known/agent-card.json`. Signed via JWS (`protected` / `signature` / `header`; `alg`, `typ`, `kid`), canonicalized per RFC 8785.

**This is a solved problem and we should stop solving it.** Capability advertisement, identity, auth scheme declaration, transport negotiation, and cryptographic integrity are all done, done well, and done by a Linux Foundation TSC. **No expiry / TTL / freshness field on the card** — which is the one thing a seat lease needs, and which is therefore precisely the delta we would have to add.

---

## Verified vs. inferred

### CONFIRMED against a primary spec

| Claim | Status | Primary evidence |
|---|---|---|
| Voting absent from A2A | **Confirmed** | Term search of `docs/specification.md`: no `vote`/`quorum`/`consensus` |
| Dissent preservation absent from A2A | **Confirmed** | Same; `REJECTED` is per-task/terminal/bilateral, with no preservation obligation |
| Voting + dissent absent from MCP | **Confirmed** | Scope statement and full feature list are tool/context only; no agent peer concept exists |
| Voting + dissent absent from ANP | **Confirmed — by the spec's own words** | ANP meta-protocol non-goals + "future versions may define … voting … and governance mechanisms" |
| Voting + quorum absent from ERC-8004 | **Confirmed** | No such functions; spec defers aggregation off-chain |
| A2A has no registration/deregistration/lease/TTL | **Confirmed** | "the current A2A specification does not prescribe a standard API for curated registries"; no expiry field on AgentCard |
| A2A extension mechanism is Agent-Card-declared + `A2A-Extensions` header, with `required` enforcement | **Confirmed** | `docs/topics/extensions.md`, spec §4.6; `ExtensionSupportRequiredError` |
| A2A extensions can define **new RPC methods** | **Confirmed (guide-level)** | "Adding entirely new RPC methods beyond the core set defined by the protocol." |
| A2A extensions **cannot** add new enum values or change core structures | **Confirmed** | "Adding New Values to Enum Types: Extensions should use existing enum values and annotate additional semantic meaning in the `metadata` field." |
| A2A has task-level human gates | **Confirmed** | `INPUT_REQUIRED`, `AUTH_REQUIRED` state definitions |
| A2A has task history, `tasks/list`, contextId grouping, signed cards | **Confirmed** | §3.1.4 ListTasks; `historyLength` semantics; JWS/RFC 8785 |
| ERC-8004 has no agent retirement | **Confirmed** | Registry function list contains no deregister/burn/retire |
| ERC-8004 supports attributed negative feedback with non-destructive revocation | **Confirmed** | `int128 value`; `revokeFeedback` sets `isRevoked`; `readAllFeedback(includeRevoked)`; `appendResponse` |
| ACP is merged into A2A | **Confirmed** | agentcommunicationprotocol.dev: "ACP is now part of A2A under the Linux Foundation" |
| No governance/voting/dissent extension exists in the A2A ecosystem | **Confirmed (negative search)** | Official+experimental extension listings: Secure Passport, Timestamp, Traceability, AGP only |
| The Kang & Diponegoro paper exists as cited | **Confirmed** | arXiv abstract page, authors and date match |

### NOT CONFIRMED / could not verify

- **The paper's per-cell "Partial" ratings.** These are self-declared as subjective: their own limitations section admits *"'Partial' classifications involve subjective judgment about construct relevance."* I did not try to reproduce them.
- **"MCP v1.1"** — the paper's row label. MCP does not version this way; revisions are dated (`2025-06-18`, `2026-07-28`). I could not map "v1.1" to any real MCP revision. Likely a paper error.
- **Whether A2A §4.6's two named extension points are exhaustive.** §4.6.2 says "several well-defined extension points" and then details only Message and Artifact Extensions. Whether that is a normative closed list or incomplete prose, I cannot tell from the text. **This is the single most important unresolved question for us** — see Assumption candidates.
- **The paper's per-claim spec citations.** The PDF text layer did not extract cleanly; I read the gap matrix and limitations via the arXiv HTML render, not the PDF. Their evidence trail for individual "Absent" cells is thin in what I could read.
- **Whether the TSC would actually accept a governance extension.** Process is documented; appetite is not.

### FOUND FALSE or indefensible

1. **A2A "Human Escalation: Absent" — false on a plain reading.** A2A ships `INPUT_REQUIRED` and `AUTH_REQUIRED` as first-class task states specifically for handing control back to a human/client. The paper defends this by narrowing to *governance* escalation ("distinct from task routing to human-backed agents"), which is a real distinction — but the cell as printed misrepresents the spec.

2. **A2A "Audit: Absent" — indefensible on the paper's own scale.** A2A has `Task.history`, `historyLength`, `contextId` correlation, a `tasks/list` query method (added in v1.0, *after* much of the ecosystem commentary the paper leans on), push-notification delivery, and JWS-signed Agent Cards. The paper rates MCP's audit "Partial" while rating A2A's "Absent" — that ordering is backwards. A2A's audit surface is strictly richer than MCP's.

3. **"A2A's extension mechanism explicitly supports 'new data, requirements, RPC methods, and state machines'" — misleadingly overstated.** That quote comes from the *non-normative guide*, not the normative spec, and the same guide immediately forbids adding new enum values or changing core data structures. A "State Machine Extension" therefore cannot introduce a `TASK_STATE_DISSENTED`. The paper uses this quote to argue our gaps are "extensible"; the constraint it omits is exactly the one that bites us.

4. **Treating ACP as a fifth independent protocol — stale.** ACP folded into A2A. Five protocols surveyed is really four families, one of them absorbed.

5. **ERC-8004 "Dissent: Absent" — overstated.** ERC-8004's Reputation Registry already implements attributed, signed-negative, non-destructively-revocable, respondable, immutably-anchored judgment records with an `includeRevoked` read filter. That is a dissent register in all but the object it points at (an agent's performance, not a project's direction). "Partial" would be the honest rating.

**Net:** the paper's *thesis* holds — governance is a missing layer, not a missing feature. Its *matrix* is sloppy in ways that flatter the thesis. It is a usable citation for "voting and dissent are absent"; it is **not** usable as evidence that A2A can painlessly carry our primitives.

---

## Surprises

1. **The paper undersells A2A and thereby oversells our opportunity.** Two of its five A2A cells are wrong in the direction of "more gap." If we cite it uncritically and a reviewer reads the spec, we lose credibility on the one assumption everything rests on. **Cite the specs, not the paper.**

2. **The paper's most quotable line for us is its least reliable.** "New data, requirements, RPC methods, and state machines" is the sentence that makes A2A look like a ready carrier. It is guide-level, non-normative, and self-contradicted three paragraphs later.

3. **The enum prohibition is the real constraint, and nobody is talking about it.** Any A2A-native encoding of DISSENT, TOMBSTONE, or LEASE-EXPIRED must live in `metadata`, reusing an existing `TaskState`. That means A2A can *transport* our primitives but cannot *typecheck* them — the semantics stay in our layer. Which is, ironically, exactly the paper's conclusion ("a missing architectural layer above current interoperability standards") arrived at by a route the paper doesn't take.

4. **ERC-8004 already built the mechanic we thought was novel.** `revokeFeedback` → sets `isRevoked`, preserves the record; `readAllFeedback(includeRevoked)` → filter it out of the default view. That is TOMBSTONE-as-ledger-entry and DISSENT-quarantined-from-orientation, shipping, on-chain, today. Our novelty is not the mechanic. **Our novelty is the object it attaches to** — a judgment about the *project*, not about an *agent*. That reframing is sharper and more defensible than "nobody preserves dissent."

5. **ANP hands us the citation the paper was trying to be.** A spec that names "Protocol consensus, voting, review, and governance mechanisms" in its own future-work section is a stronger, unimpeachable primary source than a third-party gap analysis.

6. **A2A already has TSC voting with 50% quorum and majority approval — for extensions.** The *humans* governing A2A vote. The *agents* A2A describes cannot. The governance layer exists one level up, in GitHub and a TSC, exactly where thebus puts it (issues + human gate). This is convergent evidence for our architecture, from an unexpected direction.

7. **A2A explicitly declines to standardize registries.** That is not an oversight to be filled by an extension — the extension mechanism is per-connection (`A2A-Extensions` header on a request to *one* agent). There is no fleet-level object to extend. **SEAT LEASE and TOMBSTONE are structurally out of reach of A2A extensions, not merely unimplemented.** This is a harder claim than the paper makes, and it is better for us.

8. **Agent Cards have no expiry field.** For a spec so thorough about identity and signing, the absence of any TTL/freshness on a signed capability document is a genuine hole — and it is precisely the hole a lease fills.

---

## Assumption candidates

Ranked by how much of thebus rests on them.

**A1 — LOAD-BEARING, now well-supported.** *Voting and dissent preservation are absent from all current agent interop protocols.* Confirmed against A2A, MCP, ANP, ERC-8004 primary sources; ANP says it about itself. **Promote from "rests on one paper" to "rests on four specs."** Retire the paper as sole support; keep it as a secondary citation only.

**A2 — LOAD-BEARING, needs resolution.** *Are A2A §4.6's extension points (Message, Artifact) a closed normative list?* If yes, extensions cannot add RPC methods at all and the guide's four categories are aspirational — which kills "A2A carries our primitives" outright. If no, method extensions are viable. **Cheapest resolution: open a clarifying issue on `a2aproject/A2A`, or read `a2a.proto` / the JSON-RPC binding section for whether method dispatch is open.** Do this before any A2A-alignment work is scheduled.

**A3 — REFRAMED, and better.** *thebus's novelty is not "preserving dissent" (ERC-8004 does that for agent performance) but "preserving a judgment about the project, attributed to a seat, quarantined from orientation."* Rewrite the positioning around the **object** of the judgment and the **orientation quarantine**, not around the existence of a preservation mechanic.

**A4 — Structural, and it strengthens the thesis.** *SEAT LEASE and TOMBSTONE cannot be A2A extensions, because A2A extensions are per-request and A2A has no fleet/registry object.* If A2 resolves badly this becomes moot; if A2 resolves well, this is still true and is the sharpest statement of why a governance layer must sit *above* A2A rather than inside it.

**A5 — Adopt, don't rebuild.** *Agent Cards are a solved capability-advertisement format; our harness capability profiles should be an AgentCard profile (or a data-only A2A extension) rather than a parallel schema.* Concrete: emit `.well-known/agent-card.json` per harness; put lease/seat data in an `AgentExtension` with `params`; keep `AgentSkill` as the capability unit. Cost is low, interop credibility gain is high, and the one missing field (expiry) is the exact thing we contribute.

**A6 — Timing, and it cuts both ways.** *No governance extension exists in A2A's official or experimental tiers as of Aug 2026.* True — I checked. But the paper's inference ("no demand signal") is one reading; "not yet" is another. A2A ships fast (v0.2.2 → v1.0 in eight months). **The window is real but not indefinite; treat "first mover on governance-as-A2A-extension" as a hypothesis to test cheaply (file an experimental-ext proposal issue), not a moat to plan around.**

**A7 — Scope discipline.** *MCP is not a competitor, an alternative, or a gap. It is a different layer.* Stop including it in comparison matrices except to say so.

---

## Sources

**The claim under test**
- Paper abstract, authors, date — https://arxiv.org/abs/2606.31498
- Gap matrix (Table III), extensible-vs-structural classification, limitations §V-F — https://arxiv.org/html/2606.31498v1
- PDF (text layer did not extract cleanly) — https://arxiv.org/pdf/2606.31498

**A2A — primary**
- Full specification (TaskState enum, §4.6 Extensions, AgentCard/AgentSkill/AgentCapabilities, `tasks/list`, `historyLength`, `contextId`, push notifications, JWS signing, term searches) — https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md
- Rendered specification — https://a2a-protocol.org/latest/specification/
- Extensions guide: four categories, limitations (no new enum values, no core-structure changes), `A2A-Extensions` header, `required`, security requirements — https://raw.githubusercontent.com/a2aproject/A2A/main/docs/topics/extensions.md and https://github.com/a2aproject/A2A/blob/main/docs/topics/extensions.md
- Extensions overview (rendered) — https://a2a-protocol.org/latest/topics/extensions/ and https://a2a-protocol.org/dev/topics/extensions/
- Extension & Binding Governance: tiers, `ext-`/`experimental-ext-` prefixes, URI namespace, TSC vote 50% quorum + majority — https://a2a-protocol.org/latest/topics/extension-and-binding-governance/
- Agent discovery: well-known URI, curated registries, "does not prescribe a standard API for curated registries" — https://a2a-protocol.org/latest/topics/agent-discovery/
- Life of a task: terminal vs. interrupted states, `input-required` semantics — https://a2a-protocol.org/latest/topics/life-of-a-task/
- Release history (v1.0.0 2026-03-12 incl. `tasks/list`; v1.0.1 2026-05-28 patch; v0.2.2 introduced extensions) — https://github.com/a2aproject/A2A/releases
- Project governance — https://github.com/a2aproject/A2A/GOVERNANCE.md
- Linux Foundation one-year adoption announcement — https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year

**MCP — primary**
- Latest specification revision 2026-07-28: scope, host/client/server, features, stateless requests, security principles — https://modelcontextprotocol.io/specification/latest
- Prior revision 2025-06-18 for comparison (sampling/roots/elicitation as client features, logging utility) — https://modelcontextprotocol.io/specification/2025-06-18
- Extensions mechanism, identifier format, official extension list (OAuth Client Credentials, Enterprise-Managed Authorization, MCP Apps, MCP Tasks), SEP process, negotiation via `_meta` — https://modelcontextprotocol.io/extensions/overview

**ACP — primary**
- Scope, primitives, offline discovery, and "ACP is now part of A2A under the Linux Foundation" — https://agentcommunicationprotocol.dev/introduction/welcome

**ANP — primary**
- Meta-protocol specification: bilateral negotiation, non-goals ("no global protocol registry, consensus-protocol election algorithm…"), future work ("Protocol consensus, voting, review, and governance mechanisms") — https://raw.githubusercontent.com/agent-network-protocol/AgentNetworkProtocol/main/06-anp-agent-communication-meta-protocol-specification.md
- Project root / DID (`did:wba`) and Agent Description Protocol — https://github.com/agent-network-protocol/AgentNetworkProtocol and https://agent-network-protocol.com/specs/communication.html

**ERC-8004 — primary**
- Full EIP: Identity / Reputation / Validation registries, function signatures, `int128` signed feedback, `revokeFeedback` + `isRevoked`, `appendResponse`, `readAllFeedback(includeRevoked)`, "On-chain pointers and hashes cannot be deleted", absence of deregistration, off-chain aggregation punt — https://eips.ethereum.org/EIPS/eip-8004

**Background / cross-check (not relied on for any claim above)**
- Survey of MCP/ACP/A2A/ANP — https://arxiv.org/pdf/2505.02279
- A2A architecture explainer — https://tyk.io/learning-center/a2a-protocol-architecture-and-technical-specification/
- Agent2Agent overview — https://en.wikipedia.org/wiki/Agent2Agent
