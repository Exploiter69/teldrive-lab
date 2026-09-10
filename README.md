# TelDrive Lab

Power-user ecosystem and companion tooling for TelDrive.

## Principles

- TelDrive remains the source of truth.
- Existing Telegram data is protected.
- Existing rclone mounts remain protected.
- No migration or re-upload of existing data.
- Sidecars must be disposable and rebuildable.
- Read-only consumers wherever possible.
- ₹0 / $0 infrastructure.
- Resource-conscious for the i5-1235U / 8 GB RAM host.
- Measure before changing performance settings.

## Planned areas

- Search and metadata
- Smart views
- Jellyfin / personal media
- WebDAV and interoperability
- Automation
- Monitoring and health checks
- Backup and recovery tooling
- OCR / transcription
- Local AI
- Experimental power-user features

## Protected foundation

- TelDrive production deployment
- PostgreSQL
- Telegram-backed storage
- `~/TelegramRaw`
- `~/TelegramDrive`
- existing rclone services
- existing TelDrive source repository
- Recent `created_at` fix
