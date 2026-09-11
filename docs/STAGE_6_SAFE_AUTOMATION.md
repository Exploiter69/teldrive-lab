# Stage 6 — Safe Automation & Integrations

## Goal

Automate Lab-owned operations without becoming a generic workflow platform. Stage 6 builds on the durable Phase 3 job engine, provider resilience, interoperability, and media data layers.

## MUST

- scheduled durable jobs
- event-driven ingestion
- verification after mutation
- job dependencies and bounded retries
- pause/resume/degraded behavior
- notifications using local/free mechanisms
- webhook/event emission
- explicit approval points for high-risk operations

## SHOULD

- ingestion templates
- backup/verification schedules
- archive watcher
- integration hooks for Jellyfin and external tools

## Boundaries

Schedules materialize ordinary durable jobs; they do not create a second queue. Events are persisted before downstream handling. Mutating job classes require a verification plan. High-risk cleanup/organization/restore operations require an explicit approval record. Provider degradation results in pause-and-retry guidance rather than rate-limit bypass.

Local notifications use an append-only local spool, so no paid notification provider is required. Webhook payloads are versioned event data and grant no authorization. Cross-system orchestration remains external: cron, n8n, GitHub Actions, or similar systems may consume safe events/APIs.

## Safety invariants

1. Automation never bypasses policy or authorization.
2. Scheduling never directly mutates storage.
3. A mutation is not considered successful until verification succeeds.
4. Retry counts remain bounded by the existing durable job model.
5. Provider backpressure is respected; degraded/unavailable providers are paused.
6. High-risk operations require explicit operator approval.
7. Notifications and webhooks are advisory/informational, never authority.
8. No paid service is required for Stage 6.
9. The Stage 6 gate performs no production storage mutation.
10. TelDrive Lab remains a storage control plane, not a general automation platform.

## Definition of done

The Stage 6 automation primitives, tests, and host gate pass while all existing regression tests remain green and production storage mutation remains NONE.
