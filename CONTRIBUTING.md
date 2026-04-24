# Contributing to Policy Commitment Attestation

Thank you for your interest in PCA. This repository is the canonical source for the specification and is maintained by [Dictiva](https://dictiva.com) pending contribution to the Linux Foundation [Agentic AI Foundation (AAIF)](https://aaif.io/).

## How to contribute

1. **Open an issue first** for substantive changes — edits to the data model, new evidence types, new conformance levels, new interop profiles. This lets us discuss the change before you invest in a pull request.
2. **Editorial changes** (typos, grammar, clarifications) can go straight to a pull request.
3. **Reference implementations** — if you implement PCA in a language or framework, please open an issue linking to your implementation; we'll link it from the README once stable.

## Reviewers

At v0.1, Dictiva maintainers are the sole reviewers. On AAIF adoption, governance transitions to the AAIF Technical Steering Committee process.

## Style

- Normative language (MUST / SHOULD / MAY) per [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).
- Markdown lint-clean (heading hierarchy, consistent bullet style).
- Examples in `examples/` are fully-formed credentials with placeholder proof values.

## Scope

**In scope**:

- Credential data model refinements
- Evidence type registry additions
- Conformance / interop profiles
- Security / privacy analysis
- Migration guidance between versions

**Out of scope**:

- Governance statement semantics (application-specific, not a standards concern)
- Specific implementations (those belong in their own repos, linked from README)
- Language-specific SDKs (same)

## Review criteria

Contributions are evaluated against:

- Standards composition fidelity — does the proposal compose well with W3C VC, in-toto, OSCAL, MCP Auth, ODRL?
- Backward compatibility — does the change break existing conforming implementations?
- Interop impact — does the change help or hinder multi-vendor interoperability?
- Audit traceability — does the change preserve the property that a verifier, given only the credential + public contexts, can fully evaluate commitment validity?

## License

Contributions are accepted under the Apache License 2.0 (see [LICENSE](./LICENSE)).

## Security vulnerabilities

If you believe you've found a security issue in the specification, please **do not** open a public issue. Instead, email security@dictiva.com.
