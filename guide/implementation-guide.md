# PCA Reference Implementation Guide

This guide walks through implementing a Policy Commitment Attestation (PCA) issuer and verifier using off-the-shelf W3C VC libraries, following the decisions recorded in Dictiva's [ADR-042](https://github.com/dictiva/dictiva/blob/main/docs/decisions/042-attestix-substrate-decision.md).

## Stack

- **Runtime**: Node.js 20+ (or modern browsers — W3C VC libraries are isomorphic)
- **Signing**: [@digitalbazaar/ed25519-signature-2020](https://github.com/digitalbazaar/ed25519-signature-2020) (Ed25519 VC Data Integrity)
- **VC issuance + verification**: [@digitalbazaar/vc](https://github.com/digitalbazaar/vc)
- **Document loading**: [@digitalbazaar/security-document-loader](https://github.com/digitalbazaar/security-document-loader) + a custom DID resolver
- **Canonicalization**: [@digitalbazaar/jsonld-signatures](https://github.com/digitalbazaar/jsonld-signatures) (transitive; uses RDF Dataset Canonicalization)

An alternative TypeScript-native stack is [DIDKit](https://github.com/spruceid/didkit) / Spruce libraries; the interfaces are broadly compatible.

## Minimum viable issuer

```javascript
import * as vc from "@digitalbazaar/vc";
import { Ed25519VerificationKey2020 } from "@digitalbazaar/ed25519-verification-key-2020";
import { Ed25519Signature2020 } from "@digitalbazaar/ed25519-signature-2020";
import { securityLoader } from "@digitalbazaar/security-document-loader";

// 1. Generate or load the tenant's Ed25519 issuer key.
const issuerDid = "did:web:example.com";
const issuerKey = await Ed25519VerificationKey2020.generate({
  id: `${issuerDid}#key-1`,
  controller: issuerDid,
});

// 2. Build a document loader that resolves issuer + subject DIDs.
//    For did:web, this typically fetches /.well-known/did.json.
const baseLoader = securityLoader().build();
const documentLoader = async (url) => {
  if (url.startsWith("did:web:")) {
    // Fetch + cache DID document
    return { contextUrl: null, documentUrl: url, document: await resolveDidWeb(url) };
  }
  return baseLoader(url);
};

// 3. Build the credential payload (per SPEC §3).
const credential = {
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://dictiva.io/contexts/policy-commitment/v1"
  ],
  type: ["VerifiableCredential", "PolicyCommitmentCredential"],
  issuer: issuerDid,
  validFrom: new Date().toISOString(),
  validUntil: new Date(Date.now() + 90 * 86400 * 1000).toISOString(),
  credentialSubject: {
    id: "did:web:example.com:agents:code-reviewer",
    commitment: { /* ... see SPEC §3.2 ... */ },
  },
};

// 4. Issue + sign.
const suite = new Ed25519Signature2020({ key: issuerKey });
const signed = await vc.issue({ credential, suite, documentLoader });
```

## Minimum viable verifier

```javascript
const result = await vc.verifyCredential({
  credential: signed,
  suite: new Ed25519Signature2020(),
  documentLoader,
});

if (!result.verified) {
  throw new Error(`PCA verification failed: ${result.error?.message}`);
}

// Then enforce tier floors (SPEC §4):
const tier = signed.credentialSubject.commitment.commitmentTier;
const evidence = signed.credentialSubject.commitment.evidence;
enforceTierFloor(tier, evidence); // implementation-specific
```

## DID method guidance

- **`did:web:`** (recommended default) — simple, human-readable, backed by HTTPS. Implementations MUST publish `/.well-known/did.json` for the tenant DID root, and `/<subpath>/did.json` for sub-DIDs (e.g., `did:web:example.com:agents:x` → `https://example.com/agents/x/did.json`).
- **`did:key:`** — self-describing, no hosting required. Good for ephemeral agent identities or where tenant DNS is not stable.
- **`did:ion:`, `did:ethr:`, others** — acceptable but out of scope for this guide.

## Canonical statement hash

The `statementRef.hash` field is SHA-256 over the statement body after JCS canonicalization (RFC 8785). Reference implementation:

```javascript
import { canonicalize } from "json-canonicalize";
import { createHash } from "node:crypto";

function canonicalStatementHash(statement) {
  const canonical = canonicalize(statement);
  const digest = createHash("sha256").update(canonical).digest("hex");
  return `sha256:${digest}`;
}
```

## Revocation via Status List 2021

Tenants maintain a published status list credential per [VC Status List 2021](https://www.w3.org/TR/vc-status-list/). Each issued PCA credential carries a `credentialStatus` referencing an index into that list. Revocation flips the bit at the index.

```javascript
import * as StatusList from "@digitalbazaar/vc-status-list";
const statusListCredential = await StatusList.createList({
  length: 131072, // 128K revocation slots
  statusPurpose: "revocation",
});
```

## Evidence resolution

Verifiers MUST recompute digests against referenced artifacts. For `memory_file` / `agents_md` / `skill` / `adr` evidence, this means fetching the file at its reference URI + recomputing SHA-256. Implementations SHOULD support:

- Local-path resolution (for in-tree artifacts)
- HTTPS fetch (for public artifacts)
- Git commit-pinned resolution (for repo artifacts — fetch a specific commit SHA)

## OSCAL export

For Level 2 conformance (see SPEC §6.2), credentials map to OSCAL `assessment-results` per SPEC §7.1. Reference tooling:

- [@oscal/oscal-js](https://github.com/usnistgov/OSCAL) — NIST reference library
- Implementations MAY author their own OSCAL emitter; mapping is deterministic.

## Development checklist

- [ ] Generate issuer keypair, publish DID document
- [ ] Register supported evidence types (SPEC §5.2 registry + any custom)
- [ ] Wire canonical statement hash function (JCS / SHA-256)
- [ ] Wire VC Data Integrity signing with Ed25519
- [ ] Wire credential-status publication (VC Status List 2021)
- [ ] Wire verification: proof + canonical hash recompute + evidence resolution
- [ ] Wire tier-floor enforcement (SPEC §4)
- [ ] (Level 2) Wire OSCAL assessment-results emitter
- [ ] (Level 3) Wire SCITT submission + receipt retention
- [ ] Publish JSON-LD context at the documented URL

## Common pitfalls

- **"Safe mode validation error"** — your JSON-LD context doesn't define every property used in the credential. Either publish a proper context or use `@vocab` during development.
- **"Driver for DID ... not found"** — the document loader doesn't know how to resolve your DID method. Add a resolver branch.
- **Proof verifies but credential is stale** — check `validFrom`/`validUntil` and revocation status explicitly; VC libraries typically verify cryptographic integrity only.
- **Evidence digests stop matching** — this is correct behavior when the underlying file changes. Re-issue the credential (with a new `validFrom`) and revoke the prior one.

## Reference implementation

Dictiva's smoke test at [scripts/attestix-spike/smoke-test.mjs](https://github.com/dictiva/dictiva/blob/main/scripts/attestix-spike/smoke-test.mjs) is a working, reproducible end-to-end example. Clone the Dictiva repo, `cd scripts/attestix-spike`, `npm install`, `npm run smoke`.
