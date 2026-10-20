# SemverConstraintLock design / TDD

AI-assisted prototype. Immutable public package-manifest dependency selectors are captured through independent byte/hash/schema/range derivation. A bounded SemVer subset (stable complete triples, exact/caret/tilde and comparator conjunctions) yields deterministic intersection bounds. Empty intersection is terminal CONFLICT. Otherwise owner may CAS-select one satisfying stable version once; revocation invalidates the receipt. No installation, package safety or existence-of-candidate claim.

Real pinned GenLayer JS package metadata supplies viem ^2.29.0 and typescript-parsec ^0.3.4 fixtures. Direct SDK behavior tests begin against an empty deployable class, then cover independent forged/source results, strict range parsing, 0.x caret semantics, empty intersections (explicit synthetic fixture), selection boundaries, CAS, no repeated selection and owner/revocation. Full exact SDK lint, semantic checks and schema follow.
