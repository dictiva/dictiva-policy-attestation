# PCA Example Credentials

Each file here is a fully-formed example PCA credential for illustrative purposes. Cryptographic proof values are placeholders; none verify against a real key. See [scripts/attestix-spike/smoke-test.mjs](https://github.com/dictiva/dictiva/blob/main/scripts/attestix-spike/smoke-test.mjs) in the Dictiva repo for a reproducible end-to-end issue + verify flow.

## Progression

| File | Tier | Illustrates |
|---|---|---|
| [01-minimal-t1-read.jsonld](./01-minimal-t1-read.jsonld) | T1 Read | The simplest possible credential — agent has been informed of the statement, no further commitment. Empty `evidence`, target tier is higher. |
| [02-t4-codified-with-adr.jsonld](./02-t4-codified-with-adr.jsonld) | T4 Codified | Realistic enterprise case — commitment backed by an ADR + skill + merged commit. Uses chainOfAuthority with approver. |
| [03-t6-enforced-with-hook-and-refusal.jsonld](./03-t6-enforced-with-hook-and-refusal.jsonld) | T6 Enforced | Full-featured T6 credential with ODRL refusal rules, MCP tool allowlist, PreToolUse hook, preflight check, and scope bounded to production-observation only. |

## Conventions in examples

- **DIDs** use `did:web:` for clarity; production deployments MAY use `did:key:` or other methods.
- **Canonical hashes** (`sha256:...`) are placeholder hex strings — they will not recompute from any real artifact.
- **Proof values** are placeholder multibase strings — they will not verify cryptographically. Run the smoke test in the Dictiva repo for a real round-trip.
- **Status lists** use fictional URIs — production deployments publish real status lists.
