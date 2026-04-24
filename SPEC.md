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

Each evidence entry in the `commitment.evidence` array MUST carry a recognized `evidenceKind`. The registry below is extensible: implementations MAY introduce new kinds by registering them at `https://dictiva.io/registry/evidence-kinds/` (or, post-AAIF adoption, the corresponding `aaif.io` URL). Unrecognized kinds MUST NOT cause verification to fail; verifiers SHOULD treat them as opaque carriers whose validity is determined by the associated in-toto Statement + content digest.

### 5.1 Canonical format

Every evidence entry MUST be expressible as an [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) with:

- `_type` = `https://in-toto.io/Statement/v1`
- `predicateType` = `https://dictiva.io/predicates/policy-commitment-evidence/v1`
- `subject[]` referencing the evidence artifact with at least one cryptographic digest (e.g., `sha256`).
- `predicate` carrying the PCA-specific payload (kind, description, classification metadata).

A conformant credential's inline evidence payload MAY be a shorthand — the registry row's Reference format — when the full in-toto Statement is materialized on request by the issuer.

### 5.2 Registry (v0.1)

| `evidenceKind` | Tier floors | Description | Reference format |
|---|---|---|---|
| `memory_file` | T3+ | Agent-persistent memory artifact (markdown / YAML / JSON) | Path + SHA-256 |
| `agents_md` | T3+ | Section of an AGENTS.md file | Path + section anchor + SHA-256 |
| `system_prompt_fragment` | T3+ | Identifiable system-prompt injection | SHA-256 + length |
| `adr` | T4+ | Architecture Decision Record | ADR id + canonical URI |
| `skill` | T4+ | Agent skill / capability definition | Skill name + path + SHA-256 |
| `pr_commit` | T4+ | Merged pull-request commit carrying the commitment artifact | Repo URI + commit SHA + branch |
| `bounded_context` | T5+ | Declarative scope JSON fragment (DDD-style bounded context) | SHA-256 of canonical form |
| `refusal_rule` | T5+ | ODRL prohibition or obligation expression | Inline JSON-LD or URI |
| `tool_allowlist` | T6+ | MCP / tool allowlist bound to the agent | Allowlist SHA-256 + issuer |
| `hook` | T6+ | Automation hook config (pre/post tool use, CI guard, webhook) | Config file path + selector + SHA-256 |
| `middleware` | T6+ | HTTP / RPC middleware reference | Module id + routing rule |
| `preflight` | T6+ | Preflight check reference bound to the runtime | Check id + engine + version |
| `policy_assembly_ref` | T1+ | Source policy assembly (provides chain-of-authority) | Assembly id + issuer URI |
| `semantic_similarity_report` | T2+ | Cosine / semantic similarity score against statement body | Score + evaluator + transcript digest |

**Tier floors** indicate the *minimum* tier at which a given evidence kind is valid. `memory_file` can satisfy the T3 floor but also appears in T4, T5, T6 credentials. `tool_allowlist` cannot appear at T5 or below.

### 5.3 Evidence resolution

Verifiers MUST be able to recompute any SHA-256 digest referenced by an evidence entry by fetching the artifact at the declared reference URI. Evidence whose digest no longer matches — for example, because the underlying file was edited after the credential was issued — invalidates the credential at the reported tier. Issuers SHOULD revalidate periodically (see §3.5 Revalidation) and emit a new credential when evidence integrity drifts.

## 6. Conformance

A PCA implementation MAY claim one or more of the following conformance levels.

### 6.1 Level 1 — Minimal

A Minimal implementation:

- MUST issue `PolicyCommitmentCredential`s conforming to §3 (data model).
- MUST enforce tier floors per §4.
- MUST support at least the T1, T3, and T4 tiers.
- MUST support VC Data Integrity proofs with at least the `eddsa-rdfc-2022` cryptosuite.
- MUST verify VC Status List 2021 revocation entries.

### 6.2 Level 2 — OSCAL-exporting

An OSCAL-exporting implementation additionally:

- MUST support the mapping defined in §7.1.
- MUST emit valid `assessment-results` OSCAL JSON (per the NIST OSCAL `assessment-results` schema at the cited URL) when requested.
- MUST round-trip its own credentials: every OSCAL assessment-result emitted MUST reference a verifiable underlying PCA credential.

### 6.3 Level 3 — SCITT-publishing

A SCITT-publishing implementation additionally:

- MUST be able to submit issued credentials to a SCITT Transparency Service per SCRAPI.
- MUST retain SCITT receipt pointers on the originating credential for retrieval.
- MAY publish to more than one SCITT TS and retain multiple receipts.

Implementations MAY claim higher levels only when they also satisfy all lower levels.

## 7. Interop profiles

### 7.1 OSCAL export

For [NIST OSCAL](https://pages.nist.gov/OSCAL/) (FedRAMP / NIST-aligned reporting), each `PolicyCommitmentCredential` maps to one OSCAL `observation` under an `assessment-results` document. The mapping is as follows:

| PCA field | OSCAL `assessment-results` field |
|---|---|
| `credentialSubject.id` (agent DID) | `observation.subject.subject-uuid` |
| `credential.issuer` | `observation.origin.actor-uuid` |
| `commitment.statementRef.uri` | `observation.collected.target` (control-id or statement-id reference) |
| `commitment.commitmentTier` | `observation.props[{name=pca-tier}]` |
| `commitment.evidence[]` | `observation.relevant-evidence[]` |
| `credential.proof` | `observation.origin.related-tasks[]` (as attestation reference) |
| `validFrom` / `validUntil` | `observation.collected` / `observation.expires` |
| `credentialStatus` | `observation.props[{name=pca-revocation-status-list}]` |

An OSCAL-exporting implementation MUST produce `assessment-results` that validate against the NIST OSCAL JSON schema at the profile level declared by the implementation.

### 7.2 SCITT publishing

SCITT publication per [IETF SCRAPI](https://datatracker.ietf.org/doc/draft-ietf-scitt-scrapi/) wraps the issued PCA credential into a signed SCITT Statement submitted to a Transparency Service. The Transparency Service's receipt MAY be retained on the PCA credential as an additional `proof` entry with `type = "TransparencyReceipt"` and `receipt = "<COSE_Sign1 bytes, base64url>"`.

When SCITT Architecture reaches publication as an RFC, this section will be updated with normative references and the receipt schema.

### 7.3 AGENTS.md evidence profile

When `evidenceKind = agents_md`, the reference format is:

- `uri` — canonical URI of the `AGENTS.md` file (e.g., a commit-pinned GitHub permalink).
- `sectionAnchor` — optional anchor identifying the relevant heading, e.g., `#governance` or `#security-policy`.
- `digest.sha256` — SHA-256 of the canonical UTF-8 serialization of the referenced section (or, in the absence of an anchor, the whole file).

This profile aligns with the Linux Foundation AAIF-hosted AGENTS.md convention.

### 7.4 MCP Authorization profile

Agents authenticated via the [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-11-25) (OAuth 2.1 + PKCE) MAY use the identity-token claim set to populate the credential's `credentialSubject.id` with the authenticated DID. In this profile, the issuer MUST verify the MCP identity token before issuance.

## 8. Security considerations

### 8.1 Threat model

A PCA credential asserts a commitment; it does not guarantee behavior. Verifiers MUST distinguish between:

- **Provenance** — who signed what, when, under which scope. (PCA guarantees this via VC Data Integrity + revocation.)
- **Enforcement** — whether the runtime actually obeyed the scope + refusal rules. (Out of scope for PCA; enforcement is the tier-6 evidence artifact's job. A T6 credential *references* an enforcement artifact; a verifier must separately confirm that the enforcement artifact is actually active in the runtime.)

### 8.2 Key management

- Issuer keys (tenant DIDs) MUST be rotated on compromise; old credentials MUST be re-issued or listed as revoked per §3.5.
- Agent-subject DIDs MAY be rotated without re-issuing all prior credentials, provided the old DID remains resolvable to a historical key for verification purposes. Implementations SHOULD document their DID-method's rotation behavior.
- Keys MUST use Ed25519 at minimum; additional cryptosuites MAY be supported but MUST be standardized (RFC / W3C Rec).

### 8.3 Replay + freshness

- Verifiers MUST reject credentials whose `validFrom` is in the future (clock-skew tolerance MAY be up to 60 seconds).
- Verifiers MUST reject credentials whose `validUntil` is in the past.
- Verifiers SHOULD check revocation status on every use; cached revocation responses SHOULD have a TTL no longer than the issuer's declared `revalidationInterval`.

### 8.4 Evidence tampering

- Any evidence artifact that the issuer's digest can no longer match MUST invalidate the credential at the stated tier.
- Verifiers MUST recompute digests against the current content of each referenced artifact on verification; short-circuiting via cached digests weakens the trust model.

### 8.5 Scope escalation

- Issuers MUST NOT permit a T6-Enforced credential whose `tool_allowlist` exceeds the subject's authenticated MCP permissions.
- Runtime guardrails referenced as T6 evidence MUST be verifiable as *actively installed* — not merely declared in source control.

### 8.6 Issuer impersonation

- Because PCA issuers are identified by DID, a compromised DID-method resolver (e.g., a compromised `did:web:` host) allows issuer impersonation. Deployments relying on `did:web:` MUST additionally pin issuer public keys out-of-band or use a DID method with cryptographic self-verification (e.g., `did:key:`).

### 8.7 Correlation + tracking

- Credentials identify subject agents by DID. Cross-credential correlation by `credentialSubject.id` is possible and intentional for governance observability. This is not a privacy violation for agents (non-human subjects) but see §9 for human-operator concerns.

## 9. Privacy considerations

### 9.1 Agent subjects

PCA's primary subject is a non-human agent identity. Recording that such an identity has committed to a specific policy statement does not implicate personal data.

### 9.2 Operator linkage

The `chainOfAuthority.issuedBy` and `approvedBy` fields carry DIDs, which may resolve to identifiers for human operators. Implementations MUST evaluate their jurisdiction's privacy requirements (e.g., GDPR, CCPA) before:

- Publishing credentials to public transparency logs (SCITT) that expose operator identity.
- Sharing credentials across tenant boundaries.

Where necessary, operator DIDs MAY be pseudonymous (e.g., `did:key:` with no off-chain binding to a personal name) while still providing non-repudiation within a tenant.

### 9.3 Evidence artifact content

Evidence artifacts (e.g., `memory_file` content) MAY carry tenant-confidential material. References in PCA credentials MUST therefore be:

- Access-controlled when the artifact URI resolves to restricted content.
- Content-addressed (via digest) so that verifiers can confirm integrity without the issuer re-exposing the source material.

### 9.4 Revocation privacy

VC Status List 2021 encodes revocation as bit positions in a single published list, which minimizes the metadata leaked per revocation event. Implementations SHOULD prefer Status List 2021 over per-credential revocation endpoints.

## 10. IANA considerations

### 10.1 URI registrations

This specification requests registration of:

- **Credential type URI**: `https://dictiva.io/contexts/policy-commitment/v1#PolicyCommitmentCredential`
- **Predicate type URI**: `https://dictiva.io/predicates/policy-commitment/v1`
- **Evidence predicate type URI**: `https://dictiva.io/predicates/policy-commitment-evidence/v1`

On Linux Foundation AAIF adoption, these URIs will migrate to `aaif.io/contexts/policy-commitment/v1#PolicyCommitmentCredential` (etc.), with the original URIs retaining valid historical references.

### 10.2 Media types

No new media types are registered. PCA credentials are served as existing `application/ld+json` (JSON-LD), `application/vc+ld+json` (VC), or `application/oscal-ap+json` (OSCAL).

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
