# Changelog

All notable changes to the Policy Commitment Attestation specification are documented here.

This changelog is mirrored as an [Atom feed](./changelog.atom) for subscribers.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — with the caveat that pre-1.0 versions may introduce breaking changes in any minor release.

## [Unreleased]

### Added

- Initial v0.1 draft specification: data model, credential type, Commitment Maturity Ladder (T1–T6), evidence type registry, canonical statement hash (JCS / SHA-256), proof format (VC Data Integrity Ed25519), revocation (VC Status List 2021).
- README with stack overview and maturity ladder.
- Apache License 2.0.
- GitHub Pages configuration + CNAME for `policycommitment.dictiva.com`.

### Pending

- §5 Evidence types — full registry (v0.1.1).
- §6 Conformance — levels (v0.1.1).
- §7.1 OSCAL export profile (v0.1.2).
- §7.2 SCITT publishing profile (blocked on SCITT RFC publication).
- §8 Security considerations.
- §9 Privacy considerations.
- Example credentials in `examples/`.
- Reference implementation guide in `guide/`.
- JSON-LD context definition at `https://dictiva.io/contexts/policy-commitment/v1`.

## [0.1.0] — *unreleased*

First public draft. Intended audience: Dictiva internal implementers, early external reviewers (W3C VC community, MCP working group, in-toto maintainers), and the AAIF Technical Steering Committee once proposal is submitted.

[Unreleased]: https://github.com/dictiva/policy-commitment-attestation/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dictiva/policy-commitment-attestation/releases/tag/v0.1.0
