# R3 — Media discovery and Jellyfin

R3 turns the R1/R2 catalog into a real, usable media path without giving Jellyfin authority over TelDrive storage.

## User-visible workflow

```text
TelDrive
  ↓ read-only rclone discovery
R1 Catalog
  ↓
R2 Search
  ↓
R3 media classification
  ↓
read-only filesystem exposure
  ↓
real Jellyfin
  ↓
library scan
  ↓
media stream / playback
```

## Commands

```bash
td media status
td media scan --root /path/to/a/test/media
td media verify
```

`td media scan` is read-only and reports candidates. It never moves, renames, deletes, or uploads files.

## Safety boundary

- TelDrive remains the source of truth.
- The R3 rclone command contains `--read-only` and no mutation operation.
- Jellyfin receives media with a read-only Docker bind mount.
- Jellyfin is not granted delete/rename/reorganize authority over TelDrive.
- R3 state and test configuration live in temporary/Lab-owned locations.
- The production TelDrive roots are not used by the R3 automated gate.
- R3 authentication uses Jellyfin 12's non-legacy `Authorization: MediaBrowser ...` scheme.
- The disposable Jellyfin login uses a generated password; no credential is stored in source.

## Real end-to-end gate

`scripts/r3_media_jellyfin_gate.py` creates a disposable WAV fixture, starts the official `ghcr.io/jellyfin/jellyfin:12.0` container, mounts the fixture at `/media` read-only, completes the Jellyfin startup wizard, creates a Music library, refreshes it, waits for the fixture to be indexed, and reads a real media stream through the Jellyfin HTTP API. It also inspects the container mount and requires `RW=false` for `/media`.

The gate therefore verifies the complete R3 chain:

1. **DISCOVER** — fixture is discovered through the bounded filesystem boundary.
2. **CLASSIFY** — the WAV fixture is deterministically classified as audio.
3. **EXPOSE** — Jellyfin receives the media through a controlled `/media` bind.
4. **SERVE** — the real Jellyfin server exposes the indexed item through its HTTP API.
5. **INDEX** — Jellyfin actually indexes the disposable fixture in a real Music library.
6. **PLAY** — a real media stream returns bytes from the indexed item.
7. **PROTECT** — Docker inspection proves `/media` is `RW=false`; the gate never points at production TelDrive storage.
8. **VERIFY** — the gate asserts every required condition and fails closed on errors.
9. **DOCUMENT** — this document and the roadmap/release checklist record the verified capability.

The gate is the completion authority for R3. Unit tests alone do not mark R3 complete.

## CI evidence

R3 was end-to-end verified in GitHub Actions on the R3 fix branch after the Jellyfin 12 authentication/readiness fixes. The successful run also passed pytest, R0, R1, R2, R4, R5, and the Phase 4–11 and Phase 12–22 host gates in the same CI job.

The R3 authentication regression is covered at two levels: the request unit test verifies the Jellyfin 12 `Authorization` header and `App` payload, while the configuration test verifies that the real authentication call is made with the modern authorization boundary.

## TelDrive production integration

For an operator's actual TelDrive environment, use a named rclone remote and a Lab-owned mountpoint. The exposure command is constructed as:

```text
rclone mount <named-remote> <lab-mount> --read-only --vfs-cache-mode off --dir-cache-time 10s --poll-interval 30s
```

Do not point R3 at `~/TelegramRaw`, `~/TelegramDrive`, the TelDrive production repository, PostgreSQL state, or other protected roots. First prove the isolated R3 gate, then run production preflight against a Lab-owned mountpoint.

## Completion standard

R3 is **COMPLETE**. All of the following are verified:

- media is automatically discoverable from the catalog/filesystem boundary;
- classification is deterministic and bounded;
- exposure is read-only;
- a real Jellyfin 12.0 instance starts;
- Jellyfin actually indexes the fixture;
- a real media stream is readable;
- the media bind is verified read-only;
- no TelDrive production mutation occurs;
- the automated gate passes in CI;
- the workflow is documented.
