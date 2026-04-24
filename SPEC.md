# Policy Commitment Attestation — Specification

**Version**: 0.1 (draft)
**Status**: Pre-AAIF project proposal
**Date**: 2026-04-24

> This is a working draft. Section placeholders marked *(TBD)* will be populated in subsequent revisions. Normative language (MUST / SHOULD / MAY) is used per [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 1. Introduction

### 1.1 Purpose

Policy Commitment Attestation (PCA) specifies a credential format for **verifiable commitments from AI agents to governance statements**. A PCA credential binds a specific agent identity to a specific statement version, at a declared maturity tier, with linked evidence artifacts, under a signed envelope.

### 1.2 Scope

PCA defines:

- A W3C Verifiable Credentials credential type `PolicyCommitmentCredential`
- An in-toto predicate type for the evidence payload
- A six-tier Commitment Maturity Ladder (T1–T6)
- Conformance requirements for issuers, holders, and verifiers
- Interop profiles for OSCAL export and SCITT publishing

PCA does **not** define:

- The semantic content of governance statements (out of scope; application-specific)
- Statement authoring / lifecycle
- Organizational policy for setting target tier per statement

### 1.3 Relationship to existing standards

PCA is a composition, not a greenfield design. See [README](./README.md) for the stack. Implementers familiar with W3C VC, in-toto attestations, OSCAL, and MCP Auth will find PCA natural.

## 2. Terminology

- **Agent** — an actor (typically an AI system) capable of taking actions on behalf of a principal.
- **Agent identity** — a W3C Decentralized Identifier (DID) that uniquely identifies an agent.
- **Statement** — a unit of governance policy (e.g., a control, rule, or norm) that agents may be expected to follow. Out of scope here; PCA references statements by URI + canonical hash.
- **Commitment** — an assertion by (or on behalf of) an agent that it accepts the authority of a given statement at a specified maturity tier.
- **Attestation** — a signed record of a commitment, in the form of a PCA credential.
- **Commitment tier** — one of T1–T6; see §4.
- **Evidence artifact** — a specific, addressable object (memory file, ADR, skill definition, commit SHA, etc.) that substantiates a commitment at a given tier.
- **Target tier** — the tier a statement's author expects committing agents to reach.
- **Issuer** — the party signing the PCA credential. Typically the tenant or platform acting on behalf of the agent.
- **Holder** — the agent to which the credential is bound; the subject.
- **Verifier** — any party checking the validity of a PCA credential.

## 3. Data model

### 3.1 Credential type

PCA defines a W3C Verifiable Credentials credential type `PolicyCommitmentCredential`. All PCA credentials MUST include this type in the `type` array.

```json
{
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://dictiva.io/contexts/policy-commitment/v1"
  ],
  "type": ["VerifiableCredential", "PolicyCommitmentCredential"],
  "issuer": "did:web:example.com",
  "validFrom": "2026-04-24T00:00:00Z",
  "validUntil": "2026-07-24T00:00:00Z",
  "credentialSubject": {
    "id": "did:web:example.com:agents:code-reviewer",
    "commitment": { ... }
  },
  "credentialStatus": { ... },
  "proof": { ... }
}
```

### 3.2 Commitment payload *(TBD: finalize JSON-LD context in v0.1.1)*

```json
{
  "statementRef": {
    "uri": "https://example.com/statements/stmt-001",
    "version": 3,
    "hash": "sha256:abc..."
  },
  "commitmentTier": "T4",
  "targetTier": "T4",
  "scope": {
    "tenants": ["tenant-a"],
    "entityTypes": ["process", "assembly"],
    "actionClasses": ["read", "propose_edit"],
    "refusalRules": [
      { "type": "https://www.w3.org/ns/odrl/2/prohibition", "action": "deploy", "constraint": { "env": "production" } }
    ]
  },
  "evidence": [
    {
      "type": "https://in-toto.io/Statement/v1",
      "predicateType": "https://dictiva.io/predicates/policy-commitment-evidence/v1",
      "subject": [{"uri": "memory/feedback_x.md", "digest": {"sha256": "abc..."}}],
      "predicate": {"evidenceKind": "memory_file", "description": "..."}
    }
  ],
  "chainOfAuthority": {
    "assemblyId": "ass-001",
    "issuedBy": "did:web:example.com:users:founder-a",
    "approvedBy": ["did:web:example.com:users:compliance-officer"]
  },
  "revalidationInterval": "P90D"
}
```

### 3.3 Canonical statement hash

The `statementRef.hash` field MUST be computed by:

1. Canonicalizing the referenced statement's content via [JCS (RFC 8785)](https://www.rfc-editor.org/rfc/rfc8785).
2. Computing SHA-256 of the canonical form.
3. Encoding as `sha256:<hex>`.

Statement authors MUST publish the canonical form at a resolvable URI so verifiers can recompute the hash.

### 3.4 Proof

PCA credentials MUST carry a proof per [W3C Data Integrity](https://www.w3.org/TR/vc-data-integrity/). The default cryptosuite is `eddsa-rdfc-2022` (Ed25519). Implementations MAY support additional cryptosuites.

### 3.5 Revocation

Revocation MUST use [W3C VC Status List 2021](https://www.w3.org/TR/vc-status-list/). The `credentialStatus` field references a status list URI + index.

## 4. Commitment Maturity Ladder

See [README §The Commitment Maturity Ladder](./README.md) for the tier table.

Per-tier evidence floors (normative):

- **T1 (Read)** — MUST carry at minimum: agent DID + issuance timestamp. No additional evidence required.
- **T2 (Understood)** — MUST carry a self-explanation artifact OR a reference to a semantic-similarity evaluation report with score ≥ 0.8 against the statement's canonical body.
- **T3 (Adopted)** — MUST carry at least one evidence entry of type `memory_file`, `agents_md`, or `system_prompt_fragment`.
- **T4 (Codified)** — MUST carry at least one evidence entry of type `adr`, `skill`, or `pr_commit`.
- **T5 (Bounded)** — MUST include a non-empty `scope` with at least one constraint (tenant, entity type, action class) OR at least one refusal rule.
- **T6 (Enforced)** — MUST include at least one evidence entry of type `hook`, `middleware`, `tool_allowlist`, or `preflight`.

Tiers are cumulative. A credential claiming tier N MUST also satisfy the floors of all tiers < N.

## 5. Evidence types

*(TBD: full registry in v0.1.1)*

Initial registry:

| Type | Kind | Reference format |
|---|---|---|
| `memory_file` | Agent memory artifact | Path + SHA-256 |
| `agents_md` | Section of AGENTS.md | Path + section anchor + SHA-256 |
| `adr` | Architecture Decision Record | ADR id + canonical URI |
| `skill` | Skill definition | Skill name + path + SHA-256 |
| `hook` | Automation hook config | Config file path + selector |
| `pr_commit` | Merged pull-request commit | Repo URI + commit SHA |
| `system_prompt_fragment` | System-prompt injection | SHA-256 + length |
| `bounded_context` | Scope JSON fragment | SHA-256 |
| `refusal_rule` | ODRL expression | Inline or URI |
| `tool_allowlist` | MCP / tool allowlist | Allowlist SHA-256 |
| `preflight` | Preflight check reference | Check id |
| `policy_assembly_ref` | Source policy assembly | Assembly id + URI |

Evidence entries MUST be expressible as [in-toto Statement](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) objects with `predicateType = https://dictiva.io/predicates/policy-commitment-evidence/v1`.

## 6. Conformance

*(TBD v0.1.1 — define conformance levels: Minimal, OSCAL-exporting, SCITT-publishing.)*

## 7. Interop profiles

### 7.1 OSCAL export *(TBD)*

Credentials MUST be expressible as OSCAL `assessment-results` components for FedRAMP / NIST-aligned reporting.

### 7.2 SCITT publishing *(TBD)*

Credentials MAY be published to an IETF SCITT Transparency Service per [SCRAPI](https://datatracker.ietf.org/doc/draft-ietf-scitt-scrapi/).

## 8. Security considerations *(TBD)*

## 9. Privacy considerations *(TBD)*

## 10. IANA considerations *(TBD)*

Request registration of:
- Credential type: `PolicyCommitmentCredential`
- Predicate type URI: `https://dictiva.io/predicates/policy-commitment/v1`

## 11. References

### Normative

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) — JSON Canonicalization Scheme
- [W3C VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [W3C DID v1.1](https://www.w3.org/TR/did-1.1/)
- [W3C Data Integrity](https://www.w3.org/TR/vc-data-integrity/)
- [W3C VC Status List 2021](https://www.w3.org/TR/vc-status-list/)
- [W3C ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/)
- [in-toto Attestation Framework](https://github.com/in-toto/attestation)

### Informative

- [NIST OSCAL](https://pages.nist.gov/OSCAL/)
- [IETF SCITT Architecture](https://datatracker.ietf.org/doc/draft-ietf-scitt-architecture/)
- [IETF SCITT SCRAPI](https://datatracker.ietf.org/doc/draft-ietf-scitt-scrapi/)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Agentic AI Foundation](https://aaif.io/)
- [Attestix](https://github.com/VibeTensor/attestix)
- [ISO/IEC 42001](https://www.iso.org/standard/81230.html)

---

## Appendix A — Change log

See [CHANGELOG.md](./CHANGELOG.md).
