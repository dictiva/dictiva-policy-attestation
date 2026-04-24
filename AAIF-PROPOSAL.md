# Policy Commitment Attestation — AAIF Project Proposal (draft)

**Status:** Draft · **Target:** [github.com/aaif/project-proposals](https://github.com/aaif/project-proposals) · **Date:** 2026-04-24 · **Proposer:** [Dictiva](https://dictiva.com)

> This file is the draft of the formal project-proposal submission to the Linux Foundation [Agentic AI Foundation (AAIF)](https://aaif.io/) Technical Steering Committee. Once peer-reviewed internally, the content of this file is copied (with minor format adjustments) into a pull request against `aaif/project-proposals`. Feedback on this draft is welcome via issues on this repository.

---

## 1. Project name

**Policy Commitment Attestation (PCA)**

## 2. Proposed maturity tier

**Growth** (the Foundation's starting tier for new projects, per the AAIF project lifecycle documented at [aaif.io](https://aaif.io/)).

## 3. One-sentence description

PCA is a verifiable-credential format for AI-agent commitments to governance statements — a composition of W3C Verifiable Credentials 2.0, W3C DID, in-toto attestations, NIST OSCAL, MCP Authorization, and W3C ODRL, plus a six-tier Commitment Maturity Ladder (T1 Read → T6 Enforced) with normative evidence floors.

## 4. Why AAIF

AAIF already hosts the protocol layer (MCP), the agent-instruction layer (AGENTS.md), and a reference runtime (goose). PCA is the natural fourth seat: the **commitment layer** — what has this agent committed to doing, at what maturity, signed by whom, verifiable how.

An AI-agent governance primitive is most valuable when recognized across vendors, auditors, and jurisdictions. That recognition accrues fastest inside a neutral foundation that regulators and enterprise buyers already trust — exactly the shape AAIF is building.

## 5. The problem PCA solves

Across the industry, AI-agent-governance practitioners have the same unanswered question: **when we say an agent "follows" a policy, what's the record?**

- A checkbox in an admin UI is an assertion, not evidence.
- A line in a system prompt is configuration, not attestation.
- An entry in a vendor-specific registry is a catalog, not a proof.

Meanwhile, multiple upcoming regulatory regimes — EU AI Act Article 14 (August 2026), Colorado AI Act (June 2026), ISO/IEC 42001 adoption, NIST OSCAL mandates (September 2026) — converge on the same requirement: **machine-checkable evidence that an AI agent has committed to a specific policy at a specific level of maturity, with a chain of authority anyone can verify**.

No existing standard defines that semantic unit as a single credential. W3C VC has the envelope but no domain-specific credential type. in-toto has supply-chain predicates but no policy-commitment predicate. OSCAL describes controls at the system level, not per-agent attestation. MCP Authorization handles the authentication step — not what the agent has declared to follow.

PCA fills this gap through composition. It adds one novel artifact (the Commitment Maturity Ladder) on top of well-established substrate and defines a W3C VC credential type (`PolicyCommitmentCredential`) + an in-toto predicate type (`https://policycommitment.dictiva.com/predicates/policy-commitment/v1`) that bind the composition together.

## 6. Scope (v0.1)

### In scope

- **Credential format** — a W3C VC 2.0 credential of type `PolicyCommitmentCredential`
- **Maturity ladder** — six cumulative tiers (T1 Read / T2 Understood / T3 Adopted / T4 Codified / T5 Bounded / T6 Enforced) with normative evidence floors
- **Evidence registry** — 14 evidence kinds covering the full agent-operating lifecycle (memory files, AGENTS.md, ADRs, skills, hooks, middleware, etc.)
- **Interop profiles** — OSCAL `assessment-results` export mapping; MCP Authorization integration profile; SCITT publishing profile (feature-flagged until SCITT RFC)
- **Revocation** — via W3C VC Status List 2021
- **Canonicalization** — JCS (RFC 8785) for statement hashes
- **Conformance levels** — Minimal / OSCAL-exporting / SCITT-publishing

### Out of scope

- Defining governance statements themselves (application-specific)
- Statement authoring and lifecycle (application-specific)
- Enforcement at runtime (the credential references enforcement artifacts; the runtime is the implementer's responsibility)

## 7. Existing artifacts

As of this proposal:

- **Specification** — v0.1 draft published at [policycommitment.dictiva.com](https://policycommitment.dictiva.com) ([SPEC.md](./SPEC.md))
- **JSON-LD context** — published at `https://policycommitment.dictiva.com/contexts/policy-commitment/v1`
- **Example credentials** — three progression credentials in [`examples/`](./examples/) (T1 minimal / T4 codified with ADR / T6 enforced with ODRL refusal rules + tool allowlist + PreToolUse hook)
- **Reference implementation guide** — [`guide/implementation-guide.md`](./guide/implementation-guide.md)
- **Working smoke test** — [scripts/attestix-spike/smoke-test.mjs](https://github.com/dictiva/dictiva/blob/main/scripts/attestix-spike/smoke-test.mjs) — reproducible end-to-end issue-and-verify round-trip against the DigitalBazaar TypeScript suite
- **Two published releases** — `v0.1.0-draft.1` and `v0.1.0-draft.2`
- **Architecture Decision Records** — [ADR-040](https://github.com/dictiva/dictiva/blob/main/docs/decisions/040-policy-commitment-attestation.md) (composition decision), [ADR-042](https://github.com/dictiva/dictiva/blob/main/docs/decisions/042-attestix-substrate-decision.md) (DigitalBazaar substrate choice vs Attestix)
- **Governance documents** — [CONTRIBUTING.md](./CONTRIBUTING.md), [GOVERNANCE.md](./GOVERNANCE.md) with explicit Dictiva-stewardship → AAIF-handoff transition path
- **Content cluster** — 11 blog articles explaining PCA, the ladder, the standards composition, AAIF alignment, and EU AI Act / OSCAL / SCITT / MCP Auth / Attestix interop (authored, scheduled to publish from 2026-04-25 to 2026-05-29)

## 8. Relationship to existing AAIF projects

| AAIF project | PCA relationship |
|---|---|
| **MCP** (Model Context Protocol) | PCA uses the MCP Authorization Specification (OAuth 2.1 + PKCE) for agent authentication. Token subject (DID) becomes the PCA credential's `credentialSubject.id`. |
| **AGENTS.md** | PCA defines `agents_md` as an evidence kind for T3 Adopted commitments. A section in an AGENTS.md file, content-addressed by SHA-256, is valid T3 evidence. |
| **goose** | goose agents can carry PCA credentials; a PreToolUse hook inside a goose runtime is valid T6 Enforced evidence. |

PCA complements, not competes with, each of these. It's the missing fourth piece — *commitment* — alongside *protocol*, *instructions*, and *runtime*.

## 9. Why not a Dictiva-proprietary spec

Dictiva authored the initial draft because we needed PCA to ship our commercial product. The spec will remain Apache 2.0 regardless of AAIF decision. But the value to Dictiva customers compounds when PCA is a neutral, cross-vendor standard that auditors and regulators recognize by name.

A vendor-proprietary attestation format is worth less than a Linux-Foundation-stewarded one, even to the vendor that authored it. Cross-vendor interop, regulatory reception, and open-source verifier tooling all accrete faster around a neutral home.

## 10. Governance (v0.1 → AAIF)

Until the TSC decides, the current governance model is documented in [GOVERNANCE.md](./GOVERNANCE.md):

- Proposals filed as GitHub issues labelled `proposal`
- 14-calendar-day minimum review window
- Acceptance by consensus of Dictiva maintainers
- Two-thirds majority required to overrule an explicit objection

On AAIF acceptance, governance transitions to the AAIF-standard process (TSC-mediated, community-elected maintainer roster, LF-standard contributor agreements). Apache 2.0 is retained.

## 11. Dependencies

- W3C Verifiable Credentials Data Model 2.0 (W3C Recommendation)
- W3C Decentralized Identifiers v1.1 (W3C Recommendation)
- W3C Data Integrity (W3C Recommendation)
- W3C VC Status List 2021 (W3C Recommendation)
- W3C ODRL Information Model 2.2 (W3C Recommendation)
- in-toto Attestation Framework v1 (stable)
- NIST OSCAL (active, federal mandate September 2026)
- IETF SCITT (Architecture + SCRAPI drafts, approaching RFC)
- MCP Authorization Specification (accepted Specification Enhancement Proposal)
- RFC 8785 — JSON Canonicalization Scheme

All dependencies are well-established standards or actively-developed drafts. PCA has **zero new cryptographic primitives** — Ed25519 signing, SHA-256 canonical hashing, and W3C VC Data Integrity proofs are the entirety of the crypto surface.

## 12. Initial maintainers

**Dictiva** (Carlos Alvidrez, founder, `carlos@dictiva.com`) — authored the v0.1 draft and serves as initial maintainer. Additional maintainers will be named as they join.

## 13. License

**Apache License 2.0.** The file is already committed as [`LICENSE`](./LICENSE) in this repository and matches the AAIF project-license convention.

## 14. Intellectual property

Dictiva commits to the Linux Foundation standard contributor license agreement (CLA) model. The v0.1 draft is Apache 2.0 from its first commit. No patent encumbrances are known.

## 15. Trademark

The name "Policy Commitment Attestation" and its acronym "PCA" are not currently registered trademarks. On AAIF acceptance, trademark registration is at the Foundation's discretion per standard LF practice.

## 16. Roadmap

### v0.1 (completed, April 2026)
- Core data model, maturity ladder, evidence registry
- JSON-LD context published
- Three example credentials
- Reference implementation guide
- Working smoke test

### v0.2 (target: Q3 2026)
- Finalize JSON-LD context based on review feedback
- Complete SCITT publishing profile as SCITT Architecture approaches RFC
- Expand evidence-kind registry based on community input
- Reference implementation in at least one additional language (beyond TypeScript)

### v0.3 → v1.0 (target: 2027)
- SCITT publishing profile normative (post-RFC)
- Cross-tenant federation profile
- IANA URI registration finalized
- ISO/IEC liaison statement if appropriate

## 17. Asks from AAIF

- Acceptance as a Growth-tier project
- Assignment of a technical mentor from the TSC
- Migration of the canonical repository to the AAIF GitHub organization
- Migration of the canonical URIs from `policycommitment.dictiva.com` to the AAIF-hosted equivalent, preserving historical references
- Community-review coordination with the MCP, AGENTS.md, and goose project maintainers

## 18. Community review requested from

- W3C Verifiable Credentials Working Group + Community Group
- IETF SCITT Working Group
- NIST OSCAL team
- in-toto Attestation Framework maintainers
- OpenSSF (SLSA adjacency)
- MCP Working Group (review of the MCP Authorization integration profile)
- Enterprise and regulator observers of AI-agent governance standards

## 19. Contact

- Primary: Carlos Alvidrez — `carlos@dictiva.com`
- GitHub: [github.com/dictiva/policy-commitment-attestation](https://github.com/dictiva/policy-commitment-attestation)
- Site: [policycommitment.dictiva.com](https://policycommitment.dictiva.com)
- Parent commercial entity: [Dictiva](https://dictiva.com)

---

## Appendix A — Risk register

| Risk | Mitigation |
|---|---|
| SCITT Architecture specification changes before RFC | SCITT publishing profile is feature-flagged (Conformance Level 3); v0.1 is valid without it |
| OSCAL AI-specific controls profile diverges from current drafts | PCA's OSCAL export layer is one-way (PCA → OSCAL); format changes are export-layer refinements, not breaking |
| Vendor consolidation reduces number of adopting vendors | PCA's value compounds with zero cost even to a single adopter; cross-vendor benefits are upside, not requirement |
| Alternative competing spec emerges from another vendor | Composition-heavy design means PCA can absorb adjacent work without conflict; v1.0 can cite alternatives as equivalent or superseding |
| AAIF adoption delayed or declined | Spec is publishable and usable as a Dictiva-hosted artifact independent of AAIF outcome; AAIF adoption is a brand and distribution multiplier, not a correctness precondition |

## Appendix B — Success criteria

### 6 months post-acceptance
- Credential issued by at least one non-Dictiva implementation (reference or otherwise)
- Positive review from at least one of: W3C VC CG, IETF SCITT WG, in-toto, OSCAL team

### 12 months post-acceptance
- At least three independent implementations of the issuer flow
- At least one conforming verifier not maintained by Dictiva
- Adoption by at least one regulator or standards body as a recommended format

### 24 months post-acceptance
- Graduation review toward Impact tier
- Deprecation or formal alignment of at least one competing proprietary format
