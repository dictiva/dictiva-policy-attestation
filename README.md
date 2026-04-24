# Policy Commitment Attestation (PCA)

**A specification for verifiable AI agent commitments to governance statements.**

PCA defines how an AI agent can make a verifiable, versioned, scoped, time-bound commitment to a specific governance statement — at a declared maturity tier, with linked evidence artifacts, under a signed credential envelope.

PCA is a **composition** of existing industry standards, not a greenfield invention:

| Layer | Standard |
|---|---|
| Agent identity | [W3C DID](https://www.w3.org/TR/did-1.1/) + [Attestix UAIT](https://github.com/VibeTensor/attestix) (Ed25519) |
| Agent authentication | [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-11-25) (OAuth 2.1 + PKCE) |
| Credential envelope | [W3C Verifiable Credentials 2.0](https://www.w3.org/TR/vc-data-model-2.0/) |
| Proof format | [VC Data Integrity](https://www.w3.org/TR/vc-data-integrity/) (Ed25519) |
| Evidence payload | [in-toto Statement / Predicate](https://github.com/in-toto/attestation) |
| Controls mapping | [NIST OSCAL](https://pages.nist.gov/OSCAL/) (`assessment-results`) |
| Transparency log | [IETF SCITT](https://datatracker.ietf.org/group/scitt/) (SCRAPI) |
| Rights / refusal rules | [W3C ODRL](https://www.w3.org/TR/odrl-model/) |
| Revocation | [W3C VC Status List 2021](https://www.w3.org/TR/vc-status-list/) |

The novel contribution of PCA is the **Commitment Maturity Ladder** (T1 Read → T6 Enforced) and the `PolicyCommitmentCredential` payload that binds an agent to a specific statement at a declared tier.

## Status

- **Version**: v0.1 (in draft)
- **Stage**: Pre-AAIF project proposal
- **Canonical source**: this repository
- **Canonical render**: <https://policycommitment.dictiva.com>
- **Stewardship**: Dictiva ([dictiva.com](https://dictiva.com)), intended for contribution to the Linux Foundation [Agentic AI Foundation (AAIF)](https://aaif.io/).

## The Commitment Maturity Ladder

| Tier | Name | Meaning | Floor evidence |
|------|------|---------|----------------|
| **T1** | Read | Agent knows the statement exists and binds them | Agent identity + timestamp |
| **T2** | Understood | Agent can paraphrase, cite, and surface it | Self-explanation log; semantic similarity ≥ 0.8 |
| **T3** | Adopted | Statement lives in the agent's working memory | Memory file, AGENTS.md fragment, system-prompt ref |
| **T4** | Codified | Durable repo artifact carries the commitment | ADR, skill file, PR commit |
| **T5** | Bounded | Scope constraint applied (who/what/where/refuse) | Scope JSON with ≥1 constraint, ODRL-expressed |
| **T6** | Enforced | Runtime guardrail blocks violations | Hook, middleware, MCP tool allowlist, preflight |

Tiers are cumulative — a T6 attestation must also carry T5, T4, T3 evidence.

## Quick navigation

- **[SPEC.md](./SPEC.md)** — normative specification (v0.1 outline in progress)
- **[examples/](./examples/)** — example credentials + evidence envelopes (coming)
- **[guide/](./guide/)** — reference implementation guide (coming)
- **[CHANGELOG.md](./CHANGELOG.md)** — spec changes
- **[changelog.atom](./changelog.atom)** — Atom feed for spec updates

## Why PCA

- **No existing standard defines** "agent attests to specific governance statement at specific maturity tier with specific evidence." PCA fills that gap, cleanly composed over well-understood substrates.
- **Auditor trust is compositional**: every layer PCA cites is independently recognized (W3C, IETF, NIST, Linux Foundation). A PCA credential stands up to the same scrutiny as an SBOM or SLSA provenance.
- **Agentic AI governance timing**: OWASP Agentic Top 10 (Dec 2025), EU AI Act enforcement (Aug 2026), Colorado AI Act (Jun 2026) all require machine-readable, verifiable evidence of AI agent compliance. PCA is the emitting format.

## License

Apache License 2.0 — see [LICENSE](./LICENSE).

## Contributing

This repository is the canonical source for the PCA specification. Contributions are welcome via pull request. See [CONTRIBUTING.md](./CONTRIBUTING.md) (coming).

## Background

PCA was conceived at [Dictiva](https://dictiva.com) as the mechanism behind the product's *"Governance your agents can follow"* positioning, and is being prepared for contribution to the Linux Foundation [Agentic AI Foundation](https://aaif.io/) alongside MCP, AGENTS.md, and goose. See the Dictiva ADR documenting the composition decision: [ADR-040](https://github.com/dictiva/dictiva/blob/main/docs/decisions/040-policy-commitment-attestation.md).
