# Stage 3 — Provider Resilience & Independence

Stage 3 makes Telegram important but replaceable while preserving the existing Policy → Authorization → Execution → Verification → Audit boundary.

## Roadmap coverage

- **MUST:** explicit provider abstraction/capabilities — implemented in `teldrive_lab/provider.py`.
- **MUST:** provider-independent manifest — implemented in `teldrive_lab/manifest.py`.
- **MUST:** provider health/capability discovery contract — explicit `ProviderHealth` and capability sets.
- **MUST:** resumable/retry-aware operations — explicit `RESUME` capability plus bounded retry decisions that honor provider backpressure.
- **MUST:** error classification/backpressure — deterministic provider error classes and retry delays.
- **MUST:** exportable manifests — versioned deterministic JSON read/write.
- **MUST:** evacuation/copy planning — report-only `plan_evacuation()`.
- **MUST:** degraded provider behavior — manifests and risk planning remain usable when a provider is unavailable.
- **MUST:** local metadata independent of Telegram history — stable Lab object identity is derived from local catalog identity.
- **SHOULD:** verified-copy tracking — manifest provider references carry explicit verification state.
- **SHOULD:** migration workflows — planning boundary is ready; actual migration remains a durable authorized job, not provider health logic.
- **SHOULD:** local/rclone paths — existing local transfer and rclone boundary remain the byte-moving mechanisms.

## Safety

Provider code cannot authorize production mutations. Evacuation planning performs no storage I/O. Actual copying must continue through the existing durable transfer manager and authorization boundary. No Telegram API, production database, paid service, or paid AI dependency is introduced.

## Verification

```bash
python -m pytest -q
PYTHONPATH="$PWD" python scripts/stage3_provider_resilience_gate.py
```

Stage 3 is closed only when both commands pass locally.
