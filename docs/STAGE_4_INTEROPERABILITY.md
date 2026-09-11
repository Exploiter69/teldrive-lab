# Stage 4 — Interoperability

## Goal

Make TelDrive Lab interoperable with external storage and media tooling without becoming a replacement for those tools.

## Roadmap scope

- Stable capability negotiation.
- Safe HTTP-style read/range contracts.
- rclone remains the preferred byte-transfer abstraction where applicable.
- WebDAV remains optional and is not implemented as a new storage engine here.
- Local-provider interoperability remains supported through existing transfer boundaries.
- Jellyfin integration is an integration contract, not a media-server implementation.
- Versioned webhook events provide a safe external automation boundary.
- Interoperability planning is report-only in the Stage 4 gate.

## Ownership

**TelDrive Lab owns:** policy, authorization, manifests, verification, metadata, audit, planning, and safety.

**rclone/providers own:** protocol-specific byte movement.

**Jellyfin owns:** playback, library UI, transcoding, profiles, and watch state.

**External automation owns:** cross-system orchestration after receiving explicit events.

## Safety rules

1. Capability negotiation can only intersect requested and supported capabilities.
2. HTTP ranges are bounded before any provider read is attempted.
3. Optional WebDAV/Jellyfin capabilities never become core dependencies.
4. Webhooks contain identifiers and versioned event data, not authority to mutate storage.
5. The Stage 4 gate performs no production storage mutation.
6. No new rclone replacement or media-server implementation is introduced.

## Definition of done

Stage 4 is complete when the interoperability contracts, bounded range semantics, capability negotiation, external event boundary, tests, and host gate all pass while production storage mutation remains NONE.
