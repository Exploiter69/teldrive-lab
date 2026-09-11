# Stage 2 Implementation Checklist

This is the execution checklist for the Stage 2 gate. It is intentionally evidence-driven: existing audited capabilities must be reused rather than reimplemented.

## S2.1 Installation/runtime

- [ ] Verify the canonical installation path from repository state.
- [ ] Verify runtime prerequisite checks.
- [ ] Verify required configuration validation before service startup.
- [ ] Verify optional dependency reporting is explicit.

## S2.2 Capability discovery

- [ ] Locate the existing health/capability surfaces.
- [ ] Define one canonical capability vocabulary.
- [ ] Add only missing capability aggregation.
- [ ] Add regression tests for available/unavailable optional providers.

## S2.3 Operator experience

- [ ] Verify job listing/status/retry/pause/resume surfaces.
- [ ] Verify CLI/API terminology and error semantics.
- [ ] Add only missing operator-facing glue.

## S2.4 Recovery/documentation

- [ ] Document backup/restore drill.
- [ ] Document catalog/index rebuild behavior.
- [ ] Document provider degradation behavior.
- [ ] Document Telegram operating envelope without inventing undocumented numeric limits.
- [ ] Document upgrade/migration expectations.

## S2.5 Verification

- [ ] Targeted tests pass.
- [ ] Safety tests pass.
- [ ] Host gate passes.
- [ ] Full regression passes.
- [ ] Documentation is consistent with implementation.
- [ ] Clean Git checkpoint.

## Working rule

Do not mark a checkbox complete from documentation alone. Each implementation checkbox requires repository evidence and tests where behavior is executable.
