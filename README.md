# SemverConstraintLock

AI-assisted, unaudited GenLayer Intelligent Contract prototype for capturing a fixed set of public package-manifest dependency constraints and selecting a version that satisfies their intersection. It produces an inspectable certificate. It does not install software, resolve a dependency graph, establish package safety or prove a candidate version exists in a registry.

## Independent consensus

The owner fixes one to eight distinct commit-pinned package.json URLs, exact SHA-256 byte digests, expected package names, dependency sections and one shared dependency name. Every validator independently downloads the manifests, verifies the bytes, parses strict JSON, extracts the selected constraints and computes the canonical intersection. The validator compares its complete canonical result with the leader's proposed result. A leader cannot substitute an arbitrary range, conflict flag or snapshot hash. This contract uses deterministic public-document derivation under GenLayer consensus; it makes no model-quality claim and does not call an LLM.

The source accepts HTTPS raw.githubusercontent.com URLs with a full lowercase 40-character commit and safe path segments. It rejects credentials, ports, queries, fragments, mutable branch names, empty or dot path segments and duplicate URLs. Each fetched manifest must be HTTP 200, nonempty UTF-8, no more than 48,000 bytes, match its digest and expected package name, and contain a stable complete package version. Duplicate JSON keys are rejected. Selectors support dependencies, devDependencies or peerDependencies.

## Supported version language

Versions are stable complete triples, with each component from 0 through 999999 and no leading zeros. Supported constraints are exact versions, =, ^, ~, >, >=, < and <=. A range can contain one to four comparators separated by exactly one space; they form a conjunction. Caret preserves the leftmost nonzero component, including ^0.0.x. Tilde advances the minor bound. Derived upper-bound overflow is rejected.

This is intentionally a bounded subset rather than full npm semver. Prereleases, build metadata, wildcards, partial versions, OR, hyphen ranges, workspace/file/git aliases and dist tags are rejected. The intersection checks the discrete version domain: an open interval with no representable triple is CONFLICT, even if the corresponding continuous interval would be nonempty.

## Interface and state

The deployable file is semver_constraint_lock.py. Its constructor takes no arguments and records the caller as owner. It pins the concrete official GenVM runner py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6. No wallet credential or API key is an input.

| Method | Effect |
|---|---|
| open_lock(lock_id, sources_json) | Owner creates a unique identifier of 1–64 ASCII letters, digits, underscores or hyphens. The JSON input is at most 8000 characters and fixes 1–8 source selectors for one dependency. Creates OPEN. |
| capture(lock_id) | Anyone independently captures the fixed manifests once. Stores constraints, canonical snapshot digest, intersection and retrieval time. Moves OPEN to READY or terminal CONFLICT. |
| select(lock_id, version, expected_snapshot_sha256) | Owner selects one satisfying stable version from READY using compare-and-set against the exact captured snapshot digest. Moves to SELECTED once. |
| revoke(lock_id) | Owner permanently invalidates any non-revoked lock, including a selected certificate. |
| get_lock(lock_id) | Returns the full source policy, snapshot, selection and state. |
| get_certificate(lock_id) | Returns valid only in SELECTED, with dependency, snapshot digest, selected version, bounds and selection time. |

Source selectors are objects containing exactly url, sha256, package, section and dependency. A transport, digest, JSON or unsupported-range error aborts capture without changing the OPEN lock. There is no automatic retry, refresh, renewal or background process. Reuse a new lock identifier for a different source snapshot. Revocation retains historical data; consumers must check the current certificate rather than trusting an earlier selected-version event.

## Trust and integration limits

Commit pinning establishes requested bytes, not truthful authorship, secure package contents, current compatibility or registry existence. One publisher can control multiple packages. Dependency intersections do not account for platform, peer-resolution strategy, transitive dependencies, optional dependencies or runtime behavior. The owner can choose any satisfying version; consensus does not rank candidates or certify an installation.

The pinned SDK exposes response status, headers and body, but not a final-URL or redirect-policy control. The received-byte limit is applied after download. TLS/DNS, SDK redirect handling, bandwidth and public-host availability remain transport assumptions. Only cooperating consumers who bind the expected chain, contract, lock, source selectors and snapshot digest gain the intended guarantee. Network finality and revocation handling belong to the integration.

## Verification and provenance

The checked source hash is recorded in evidence/verification.json. Sixteen direct SDK tests pass, alongside exact-SDK semantic lint and ABI extraction. Tests cover independent-source/leader divergence, strict JSON and range parsing, 0.x caret behavior, incompatible and discretely empty intersections, selection bounds, snapshot compare-and-set, owner authority, one-time selection and revocation. The real red regression for a discretely empty interval is retained in evidence/tdd-discrete-red.log.

Run Python 3.12+ in a dedicated virtual environment, install requirements.txt, then run tools/verify.py. The verifier downloads official GenVM v0.2.12 containing the exact pinned runner and uses the actual SDK contract and storage implementation. Test-only Windows compatibility in tests/conftest.py defers an upstream open-stdin cleanup and refreshes gltest warp metadata. It does not replace consensus logic.

fixtures/sources.json identifies a real commit-pinned GenLayer JS manifest snapshot. Direct tests mock transport using those captured bytes; deliberately conflicting manifests are synthetic. Fixture retrieval dates are provenance notes rather than proof of a live consensus fetch. Deployment, live HTTP consensus and production behavior remain unverified; no users, audit or deployed application are claimed.

Official references: [GenLayer boilerplate](https://github.com/genlayerlabs/genlayer-project-boilerplate), [direct testing API](https://github.com/genlayerlabs/genlayer-testing-suite/blob/main/docs/direct-runner.md), [exact SDK release](https://github.com/genlayerlabs/genvm/releases/tag/v0.2.12), and [captured GenLayer JS manifest](https://github.com/genlayerlabs/genlayer-js/blob/1b7f50a3a3f2963ea857941b0fb386081dd5c326/package.json).

MIT licensed; see LICENSE.


## Commit locator namespace repair (2026-10-21)

The prior local source SHA256 `8d9001f2fa17f911e9efe60e71d84a3655da0eb73d7e4a1048f3839891239c6b` is superseded by `9b6b1136b0bca3313e95fae6335078992ce8b87f29e839aa8278c977bdb5374d`. Literal repository `.` and `..` segments are now rejected before registration or fetching, alongside the existing path restrictions. Legitimate `.github`, `repo.name` and `_repo` names remain accepted. The previous defect concerned the declared repository/commit locator under dot-segment URL normalization; exact expected SHA256 byte checks remained effective. No arbitrary-byte bypass is claimed.

The actual public SDK API regression first produced 2 failures and 3 valid-name passes. The repaired full suite has 21 passing tests, full semantic validation and schema extraction succeed on GenVM v0.2.12, and the extracted public schema is byte-identical. See `evidence/namespace-fix.json`, `namespace-red.log` and the current `verification-*.log`. Previous counts/reviews describe their frozen historical candidates; Root independently reviewed this narrow correction and closed it after the fix; see `evidence/namespace-final-review.json`. No deployment or live exploit is claimed.


## Recorded Studio constructor deployment

The constructor deployment in deployment.json is FINALIZED/SUCCESS on the free GenLayer Studio testnet (61999), NORMAL full consensus, value0. Its source bytes match this exact file. This does not verify a real public catalog or the register/lock/revoke business lifecycle. Earlier null/deployment statements and logs describe local pre-deployment evidence. No portal submission or acceptance is claimed.
