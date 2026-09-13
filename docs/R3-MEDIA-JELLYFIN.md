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

## Real end-to-end gate

`scripts/r3_media_jellyfin_gate.py` creates a disposable WAV fixture, starts the official `jellyfin/jellyfin` container, mounts the fixture at `/media` read-only, completes the Jellyfin startup wizard, creates a Music library, refreshes it, waits for the fixture to be indexed, and reads a real media stream through the Jellyfin HTTP API. It also inspects the container mount and requires `RW=false` for `/media`.

The gate is the completion authority for R3. Unit tests alone do not mark R3 complete.

## TelDrive production integration

For an operator's actual TelDrive environment, use a named rclone remote and a Lab-owned mountpoint. The exposure command is constructed as:

```text
rclone mount <named-remote> <lab-mount> --read-only --vfs-cache-mode off --dir-cache-time 10s --poll-interval 30s
```

Do not point R3 at `~/TelegramRaw`, `~/TelegramDrive`, the TelDrive production repository, PostgreSQL state, or other protected roots. First prove the isolated R3 gate, then run production preflight against a Lab-owned mountpoint.

## Completion standard

R3 is complete only when all are true:

1. media is automatically discoverable from the catalog/filesystem boundary;
2. classification is deterministic and bounded;
3. exposure is read-only;
4. a real Jellyfin instance starts;
5. Jellyfin actually indexes the fixture;
6. a real media stream is readable;
7. the media bind is verified read-only;
8. no TelDrive production mutation occurs;
9. the automated gate passes in CI;
10. this workflow is documented.
