# Release Hardening Contract

This document records the release-hardening decisions made after completion of the product roadmap.

## Safety boundary

TelDrive Lab keeps its historical protected production paths as immutable defaults. A deployment on a different host may **add** production roots/state through environment variables:

- `TELDRIVE_LAB_PROTECTED_ROOTS` — additional production roots, separated by the platform path separator (`:` on Linux/macOS).
- `TELDRIVE_LAB_PROTECTED_STATE` — additional protected state files/sockets, separated by the platform path separator.

Configured paths are additive only. Environment configuration cannot remove the built-in protected paths. This is intentional: configuration may strengthen the boundary, never weaken it.

For a non-default host, operators should explicitly configure the actual TelDrive production root(s) before enabling any mutation-capable workflow.

## Authorization

Mutation authorization is scope-bound. Callers must provide an `AuthorizationReceipt` whose:

1. operation exactly matches the requested mutation;
2. normalized path set exactly matches the requested paths; and
3. `approved` value is true.

The old `explicit_authorization=True` boolean path has been removed from the transfer and safety APIs. This prevents a bare boolean from acting as a reusable authorization capability.

Protected production mutation remains denied even when a valid receipt is supplied.

## CI release gate

Continuous integration runs the full test suite and the Stage 8 advanced-experiments gate. Stage 8 remains an experimental boundary, not a production feature promotion mechanism.

## Release interpretation

Roadmap completion does not itself constitute a v1.0 release. A v1.0 candidate additionally requires:

- clean installation validation;
- operator workflow validation;
- release documentation;
- green CI and local gates; and
- a final production-boundary audit.

No production TelDrive database writes, destructive autonomous storage operations, paid dependencies, or autonomous AI authority are introduced by release hardening.
