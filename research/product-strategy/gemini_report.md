TelDrive: Independent Product Strategy,
Ecosystem, and Capacity Research
A. Executive Summary
An exhaustive architectural and product strategy analysis of the TelDrive ecosystem reveals a
critical divergence between the project’s foundational engineering success and its conceptual
product roadmap. The engineering foundation established through Phase 0–22 has
successfully implemented a deterministic, durable control plane for Telegram-backed storage,
featuring robust durable jobs, isolated transfers, and audit boundaries. However, the broader
product vision is encumbered by immense scope creep, particularly regarding experimental
artificial intelligence features, bidirectional synchronization concepts, and aspirations to build a
native Over-The-Top (OTT) media platform.
The core thesis of this independent research is that Telegram is a highly volatile, strictly
governed messaging platform, not a limitless enterprise storage substrate. Building a
monolithic application that assumes perpetual, unrestricted access to Telegram's infrastructure
introduces unacceptable operational risk. Furthermore, attempting to natively build
resource-intensive capabilities—such as video transcoding, adaptive bitrate streaming,
vector-based AI search, and complex multi-client synchronization—directly contradicts the
project's strict ₹0 zero-cost infrastructure mandate. Genuine zero-cost operation dictates that
the system must run efficiently on constrained hardware, such as single-board computers or
low-tier virtual private servers, lacking discrete GPUs or massive memory allocations1.
Consequently, TelDrive must pivot away from becoming a monolithic media platform or an
uncontrolled AI laboratory. It must instead solidify its identity as an intelligent,
protocol-agnostic "Storage Operating System." By explicitly delegating heavy workloads to
mature open-source ecosystems—leveraging rclone for virtual file systems, Jellyfin for media
consumption, and SQLite FTS5 for zero-cost full-text search—TelDrive can maximize its
engineering leverage. This strategy ensures deterministic safety, respects hardware
constraints, and provides the architectural decoupling necessary to survive the inevitable
upstream rate limits and access restrictions imposed by its primary storage provider.
B. Product Identity
The strongest, most defensible, and architecturally sound product identity for TelDrive is a
Storage Operating System ("An intelligent control plane for personal storage").
This identity explicitly rejects the "Media Cloud/OTT" and "Telegram-Backed NAS" monikers.
Marketing TelDrive as a native OTT demands the development and perpetual maintenance of
client applications across dozens of distinct form factors, alongside real-time hardware
transcoding pipelines that are functionally impossible to operate securely and performantly on
a ₹0 budget3. Similarly, branding the platform as a "Unified Personal Data Platform" invites
feature bloat, encouraging the integration of unstructured data processing that dilutes the core
storage mission.
By adopting the "Storage OS" identity, TelDrive positions itself as a deterministic orchestration
layer. It sits between volatile, remote storage backends—such as Telegram, S3, or
WebDAV—and mature, specialized consumption ecosystems like Jellyfin, Nextcloud, or
automated workflow managers like n8n. TelDrive's distinct value proposition is not rendering
video or processing heavy AI models; its value lies in durably tracking manifests, managing
chunked uploads through hostile API rate limits, verifying cryptographic integrity, and exposing
a unified, standardized interface to external applications. This identity leverages TelDrive's
existing Phase 0–22 durable execution engine, transforming it from a mere Telegram wrapper
into a robust infrastructure plane.
C. Core Product Pillars
The evolution of the TelDrive product must be strictly anchored to six non-negotiable
architectural pillars to ensure sustainability and alignment with the zero-cost mandate.
Deterministic Safety First All file mutations, including moves, deletions, and deduplication
routines, must be executed exclusively by deterministic, durable workers. Artificial intelligence,
regardless of the underlying model's sophistication, must remain strictly in an advisory
capacity. AI mechanisms may classify data or recommend archives, but they are explicitly
barred from independently authorizing production storage mutations. The safety boundary of
Policy, Authorization, Execution, Verification, and Audit must remain absolute.
Provider Independence While Telegram serves as the initial zero-cost backend, the
architecture must treat it as an untrusted, highly restrictive, and entirely replaceable module.
TelDrive must maintain its own independent metadata index and manifest registry. The system
must operate with identical logic and reliability if the underlying byte-chunks are migrated from
Telegram channels to an S3-compatible provider or a local disk array5.
Strict Ecosystem Delegation TelDrive must aggressively refuse to rebuild established, mature
open-source technologies. Complex file system abstractions, such as FUSE mounting and
chunked cryptography, belong strictly within the purview of rclone6. Media playback, library
management, and real-time hardware transcoding belong entirely to Jellyfin or similar
dedicated media servers4. TelDrive's responsibility ends at the storage abstraction and API
boundary.
Zero-Cost Pragmatism The architecture assumes the deployment environment is a
low-power, modest Linux machine. Features requiring massive memory footprints, such as
Meilisearch or Elasticsearch for indexing, or discrete GPUs for local large language models like
Ollama, must be strictly optional and modular1. The core platform must degrade gracefully and
remain fully functional without these components, relying on highly optimized local tools like
SQLite for primary operations9.
Standardized Interoperability TelDrive's primary outbound communication methodology
must rely on standardized protocols. By natively implementing WebDAV and HTTP REST,
TelDrive allows any existing application, operating system, or automation tool to read and write
to the storage fabric without requiring proprietary, TelDrive-specific API adapters.
Immutable Auditability Every system action must generate a cryptographically verifiable and
immutable audit trail. Whether a file is deleted by a human user via the Control Center, purged
by an automated retention policy, or modified following an AI-suggested organization plan, the
action must be permanently logged. This ensures complete transparency and enables rapid
rollback or forensic analysis in the event of accidental data loss or unauthorized access
attempts.
D. Real-World Ecosystem Findings
An extensive analysis of real-world deployments involving Telegram-backed storage, rclone
integrations, and media servers reveals distinct usage patterns, widespread architectural
misunderstandings, and significant operational friction among self-hosters. Users are
attempting to stretch messaging infrastructure far beyond its intended design, leading to
inevitable failures.
The most prevalent workflow is the "Free Cloud NAS," where users combine a Telegram
wrapper, rclone, and Jellyfin or Plex to host massive media libraries6. Users attempt to stream
high-bitrate video directly from Telegram's servers. Because video playback requires
continuous chunked reading and random seeking, users frequently configure the rclone mount
with aggressive caching parameters, specifically utilizing full VFS cache modes and high
read-ahead limits to prevent stream buffering12. This configuration forces rclone to
aggressively pre-fetch data from Telegram, rapidly filling the host machine's local disk space14.
When the local disk reaches total capacity, the eviction algorithms often fail under heavy I/O
contention, causing the entire media server stack to crash and occasionally corrupting local
SQLite databases15. The unmet need here is not better caching, but rather a direct read-only
contract that feeds HTTP byte-range streams directly from Telegram to the media server,
bypassing the local disk entirely.
A second recurring pattern involves multi-account load balancing to circumvent Telegram's
strict upload throttling. Users employ tools like UnLim or various open-source Python scripts to
distribute file uploads across multiple Telegram Bot tokens or user accounts19. This manual
orchestration inevitably leads to fragmented storage arrays. When a single bot is banned or a
session expires, users are left with orphaned files in abandoned channels and a desynchronized
local database21. TelDrive has an opportunity to productize this by acting as a distributed load
balancer, mapping file chunks across a registry of trusted bots while maintaining a centralized,
durable manifest that survives individual token bans.
Finally, users frequently attempt bidirectional syncing workflows, combining tools like rclone
bisync with Telegram backends to mirror local hard drives23. This workflow is fundamentally
unsustainable. Bidirectional synchronization requires constant state polling to detect remote
modifications. Against the Telegram MTProto API, this aggressive polling generates excessive
flood waits and connection resets25. Furthermore, rclone bisync remains an experimental
command prone to catastrophic data loss if state files are corrupted or conflict resolution logic
fails24. TelDrive must explicitly reject bidirectional syncing, instead offering a unidirectional,
immutable "Archive and Snapshot" model that eliminates the need for constant remote state
polling.
E. Telegram Capacity & Risk Report
The pervasive community assumption of "unlimited cloud storage" regarding Telegram is a
dangerous marketing myth. Telegram employs sophisticated heuristic anti-abuse models, and
designing an architecture that assumes perpetual, unmetered access will result in permanent
account termination20. TelDrive must operate strictly within a conservative, mathematically
modeled engineering envelope.
The analysis of documented constraints versus observed community behavior highlights
several critical boundaries. Officially, Telegram enforces a maximum file size of 2GB for
standard users and 4GB for Premium subscribers28. However, the standard Telegram Bot API
enforces a severe 50MB upload limit and a 20MB download limit. To access the 2GB threshold
programmatically, the architecture must utilize a self-hosted Local Bot API server or interface
directly via the MTProto protocol30. While there is no published aggregate storage quota,
accounts that rapidly ingest multi-terabyte archives are routinely flagged for abuse and
subsequently banned, demonstrating that "unlimited" applies strictly to organic messaging
behavior, not enterprise data warehousing33.
Rate limits represent the most significant operational bottleneck. The Telegram API enforces a
global limit of approximately 30 requests per second32. Exceeding this, particularly through
concurrent media fetching or aggressive directory scanning, triggers severe 420 FLOOD_WAIT
exceptions26. The underlying MTProto clients, such as gotd/td, implement connection pooling
and middleware to handle these errors, but the application layer must respect the requested
sleep durations, which can range from seconds to hours36.
Based on these constraints, we can define strict operational envelopes for TelDrive:
 Operating Envelope                              Characteristics and Viability


 Sustainable Envelope                            Represents low-risk, responsible usage.
                                                 Uploads are strictly sequential, utilizing a
                                                 Local Bot API server. The system enforces a
                                                 token-bucket rate limiter, artificially pausing
                                                 between chunk uploads. Background
                                                 synchronization is scheduled during
                                                 off-peak hours, and total daily data
                                                 ingress/egress is hard-capped to mimic
                                                 heavy but organic user activity.


 Aggressive Envelope                             Represents moderate risk. The system
                                                 employs parallel uploads distributed across
                                                 multiple authenticated bot tokens. It utilizes
                                                 aggressive read-ahead caching for
                                                 high-bitrate video streaming. This envelope
                                                  guarantees intermittent 420 FLOOD_WAIT
                                                  errors; survival depends entirely on the
                                                  implementation of durable execution,
                                                  exponential backoff, and robust session
                                                  recovery mechanisms.


 Red-Zone Behavior                                Architecturally irresponsible. This involves
                                                  exposing the Telegram backend directly to
                                                  multiple concurrent users, serving as a
                                                  pseudo-CDN for 4K video streams, or
                                                  executing continuous, 24/7 read/write
                                                  cycles for active database files. This
                                                  behavior will quickly trigger automated
                                                  heuristic abuse detection and permanent
                                                  bans.


 No-Go Behavior                                   Strictly prohibited. This includes providing
                                                  mechanisms for automated account
                                                  creation (farming) to evade bans,
                                                  attempting to circumvent hard file size
                                                  limits via undocumented exploits, or
                                                  configuring the client to aggressively retry
                                                  operations without adhering to the explicit
                                                  sleep durations mandated by Telegram's
                                                  flood waits.



TelDrive must architect around Telegram as an unreliable, heavily metered external storage
substrate, not an effectively unlimited backend. Treating the provider as hostile ensures the
application logic remains resilient when constraints tighten.
F. Telegram Dependency Recommendation
Telegram must be treated as a Replaceable Backend Provider, and under no circumstances
should it serve as the core identity of the platform.
Architecting a complex storage control plane so tightly around a single consumer messaging
application that it cannot function independently is a fatal design flaw. Telegram's primary
business objective is facilitating communication, not subsidizing free global file hosting. If
Telegram alters its Terms of Service, implements a hard 500GB storage cap, degrades MTProto
file chunking performance, or aggressively bans automation, a Telegram-monolithic TelDrive
ceases to exist entirely.
TelDrive's storage abstraction layer must treat Telegram exactly as it would treat an AWS S3
bucket, a Backblaze B2 vault, or a local ZFS pool37. TelDrive must exclusively own and manage
the metadata—the hierarchical index, the cryptographic relationships, the file names, and the
tags. The backend provider, whether Telegram or an alternative, is treated merely as a dumb
repository for encrypted binary chunks. By maintaining this strict separation of concerns, the
control plane ensures that users can seamlessly migrate their manifests and byte-chunks to an
S3-compatible provider or a local NAS using built-in migration tools the moment their Telegram
account is restricted5. Telegram is the zero-cost catalyst for adoption, but the provider
abstraction is the mechanism for long-term survival.
G. rclone Strategy
rclone is the industry-standard utility for cloud storage orchestration, boasting over a decade
of edge-case hardening and vast community support7. Attempting to rebuild its core
functionalities within TelDrive is a textbook architectural trap. TelDrive must strategically
leverage rclone for complex low-level operations while retaining authority over high-level
intelligence and metadata.
TelDrive must explicitly delegate Virtual File System (VFS) mounting to rclone. Rebuilding a
custom FUSE driver to expose storage natively on Linux, macOS, and Windows is a massive
engineering undertaking fraught with OS-level kernel complexities, file locking nuances, and
caching edge cases. rclone mount already possesses sophisticated VFS caching algorithms,
handling sparse files and asynchronous read-ahead buffering perfectly39. Similarly, TelDrive
must delegate client-side encryption. rclone crypt provides extensively audited,
zero-knowledge encryption5. TelDrive should merely orchestrate the generation and storage of
configuration parameters, passing them to rclone, rather than inventing a proprietary
cryptographic wrapper that introduces severe security risks. Finally, bandwidth throttling, retry
logic during network timeouts, and raw byte transfer execution should be offloaded to rclone
processes where applicable, as it handles transient network failures far more elegantly than
bespoke code41.
Conversely, TelDrive must retain absolute ownership of the metadata index. rclone is inherently
stateless; it relies on querying the remote provider for directory structures and file properties.
Against an API as restrictive as Telegram's, recursive directory listings are catastrophically slow
and expensive. TelDrive must maintain a high-speed, local database (such as SQLite)
representing the entire file hierarchy, serving instant directory listings and search queries
without executing a single network request to Telegram. Furthermore, TelDrive must own job
orchestration. rclone lacks a durable, transactional queue for background tasks. TelDrive is
responsible for the durable execution of snapshot generation, media metadata extraction, and
asynchronous duplicate detection, utilizing rclone only as the execution tool for the final byte
movement.
H. OTT Decision
The broader TelDrive product vision flirts dangerously with becoming a native media platform,
encompassing watch histories, resume points, and polished library interfaces. This research
explicitly recommends Option B: TelDrive + Jellyfin Integration. TelDrive must NOT build an
OTT.
Building a credible, modern OTT platform is a monumental undertaking. It requires developing a
real-time transcoding engine capable of adaptive bitrate streaming, which fundamentally
necessitates hardware acceleration via discrete GPUs and FFmpeg4. A zero-cost project
intended to run on modest hardware cannot sustainably support this. Furthermore, an OTT
requires dedicated client applications across a fragmented ecosystem: Web, Android, iOS,
Android TV, Apple TV, Roku, and proprietary smart TV OSs. It also demands a robust metadata
scraper for posters, cast lists, and subtitles.
Comparing the architectural options highlights the fallacy of Option A (Build Complete OTT). It
diverts critical engineering resources away from storage stability toward front-end
development, ensuring both systems remain mediocre. Option C (Custom Lightweight Web
Client) offers a poor user experience, as web browsers lack widespread codec support, forcing
server-side transcoding. Option D (Hybrid) introduces unnecessary complexity.
Option B is the only viable path. Jellyfin is a mature, open-source media server with established
clients across every major platform42. TelDrive should build a highly optimized "Jellyfin Proxy
Contract." In this architecture, TelDrive handles the WebDAV abstraction and the complex
translation of Telegram byte-chunks into standard HTTP range requests, while Jellyfin is simply
pointed at the TelDrive mount as its storage directory. TelDrive remains a robust, invisible
backend; Jellyfin remains the polished frontend. This leverages millions of hours of existing
open-source development and guarantees a superior user experience at zero cost.
I. WebDAV / Interoperability Strategy
To succeed as a Storage Operating System, TelDrive must be universally accessible by existing
software ecosystems without requiring proprietary SDKs. Standard protocols guarantee
immediate, frictionless adoption.


 Protocol                         Classification                  Implementation Strategy
                                                                  and Rationale


 WebDAV                           Core                            TelDrive must build a native
                                                                  WebDAV server. This is
                                                                  non-negotiable. WebDAV
                                                                  allows native, driverless
                                                                  mounting in Windows
                                                                  Explorer, macOS Finder, and
                                                                  direct integration with
                                                                  mobile applications like iOS
                                                                  Files and various media
                                                                  players.
 HTTP REST API                   Core                            A comprehensive JSON API
                                                                 is required for the control
                                                                 plane. This allows external
                                                                 systems to trigger durable
                                                                 jobs, query the high-speed
                                                                 metadata index, and ingest
                                                                 data programmatically.


 S3-Compatible                   Important                       Highly desirable for the
                                                                 product roadmap. Exposing
                                                                 TelDrive as an
                                                                 S3-compatible endpoint
                                                                 allows enterprise-grade
                                                                 backup tools (e.g., Restic,
                                                                 Borg, Duplicati) to utilize
                                                                 TelDrive natively as a
                                                                 remote vault5.

 FUSE / Filesystem               Adapter (Delegate)              TelDrive should not write
                                                                 custom C/Go FUSE drivers.
                                                                 Instead, it should rely
                                                                 entirely on users running
                                                                 rclone mount to connect to
                                                                 TelDrive's native WebDAV or
                                                                 REST API, bridging the gap
                                                                 to the local OS file
                                                                 system40.

 SMB / NFS                       Do Not Build                    These legacy protocols
                                                                 entail immense complexity,
                                                                 heavy overhead, and
                                                                 require complex user
                                                                 permission mapping. They
                                                                 are entirely redundant if a
                                                                 robust WebDAV server and
                                                                 rclone FUSE adapter are
                                                                 supported.


J. Automation Strategy
A mature storage platform requires automation, but the architecture must rigidly define the
boundary between internal storage lifecycle management and external application logic to
maintain deterministic execution.
Internal Automation (Owned by TelDrive): TelDrive must natively orchestrate tasks that are
critical to the cryptographic health and structural integrity of the storage substrate. This
includes periodic integrity verification jobs, utilizing SHA-256 validation to ensure byte-chunks
have not silently corrupted. It also includes the automated creation of snapshots, the
enforcement of retention lifecycles, and asynchronous deduplication routines. Crucially,
TelDrive must own orphaned file garbage collection, executing background tasks to reconcile
the local database state against the remote Telegram channel state, ensuring deleted files do
not permanently consume remote quota22. These operations run on the internal durable
execution engine.
External Automation (Delegated to Ecosystem): TelDrive must explicitly refuse to build a
visual workflow editor or a complex, multi-conditional trigger system (e.g., executing a script if
a specific email arrives). Developing a bespoke automation engine replicates existing, superior
tools. Instead, TelDrive should delegate external logic to established open-source automation
platforms like n8n, Home Assistant, or standard cron jobs. TelDrive achieves this integration
simply by emitting Webhooks upon state changes (e.g., file uploaded, job failed) and exposing
its REST API to accept command triggers from these external systems.
K. AI Strategy
Artificial Intelligence presents a significant risk of scope explosion and hardware
incompatibility. The strategy must be strictly confined to Level 1 (AI-assisted search) and
Level 2 (AI-generated recommendations).
The prompt principles dictate that AI must never independently authorize production mutation.
TelDrive must enforce the deterministic safety boundary: AI proposes → policy decides →
authorization permits → executor mutates → verification proves → audit records.
Zero-Cost Feasibility and the Hardware Reality: Running local large language models (via
Ollama or llama.cpp) requires a minimum of 8GB to 16GB of system RAM, AVX2 CPU instruction
sets, and practically necessitates a discrete GPU for acceptable inference speeds2. This
completely violates the mandate to support modest hardware and ₹0 infrastructure. Therefore,
all AI extraction features—including OCR via Tesseract, speech-to-text via Whisper, vision
models, and semantic embeddings—must be strictly optional. They must execute
asynchronously via isolated background workers. If the host machine lacks the requisite
hardware, the system must gracefully bypass these steps and function flawlessly as a
deterministic storage engine.
The Search Engine Architectural Trap: Implementing semantic search introduces a critical
infrastructure decision. Popular modern search engines like Meilisearch utilize LMDB (Lightning
Memory-Mapped Database) to map entire indexes directly into virtual memory. While
incredibly fast, this approach consumes massive amounts of virtual RAM and causes severe
CPU spikes during indexing on low-end hardware, frequently crashing constrained VPS
environments1. Typesense, conversely, holds the entire index in physical RAM, strictly capping
the dataset size based on available memory46.
TelDrive must reject these heavy dependencies and default to SQLite FTS5 (Full-Text Search)
as the core search architecture. SQLite FTS5 is lightweight, embedded directly within the
application binary, incurs zero external process overhead, and is heavily optimized for
disk-based retrieval47. When configured with PRAGMA journal_mode = WAL and PRAGMA
synchronous = NORMAL, it provides exceptional concurrent read/write performance suitable
for millions of rows on minimal hardware9. Hybrid search capabilities (lexical combined with
semantic) can be achieved by utilizing FTS5 alongside lightweight local vector extensions (like
sqlite-vec), preserving the zero-cost reality while delivering intelligent retrieval49.

L. Product Completeness Matrix
This matrix exhaustively evaluates the features discovered across project documentation,
ecosystem research, and competitive analysis, classifying them by implementation status and
architectural viability.


 Feature Area        Specific           Category            ₹0 Feasible        Recommende
                     Capability                                                d Action &
                                                                               Priority


 Foundation          Durable Jobs       🟢                   Yes                Maintain.
                     Engine             IMPLEMENTED                            Foundational
                                        + TESTED                               for safety.
                                                                               (Priority 1)


 Foundation          Audit Logging      🟢                   Yes                Maintain.
                                        IMPLEMENTED                            Crucial for
                                        + TESTED                               immutable
                                                                               verification.
                                                                               (Priority 1)


 Telegram            Isolated           🟢                   Yes                Enhance. Core
                     Transfers          IMPLEMENTED                            to MTProto
                                                                               upload
                                                                               stability.


 Telegram            FloodWait          🟡 PARTIAL           Yes                MUST BUILD.
                     Handling                                                  Aggressive
                                                                               backoff is
                                                                               mandatory to
                                                                               prevent bans26.
                                                                               (Priority 2)
Telegram          Multi-Bot Load   ⚪ FUTURE       Yes   SHOULD
                  Balancing                             BUILD.
                                                        Distribute
                                                        loads across
                                                        trusted tokens
                                                        to evade limits.
                                                        (Priority 5)


Storage           Garbage          🟡 PARTIAL      Yes   MUST BUILD.
                  Collection                            Fix DB/Channel
                                                        state
                                                        mismatches22.
                                                        (Priority 3)

Storage           Deduplication    🟠              Yes   SHOULD
                                   EXPERIMENTAL         BUILD.
                                                        SHA-256
                                                        detection
                                                        prevents
                                                        duplicate
                                                        uploads.


Storage           Snapshots /      🟡 PARTIAL      Yes   MUST BUILD.
                  Backup                                Essential for
                                                        disaster
                                                        recovery and
                                                        immutability.


Interoperabilit   WebDAV           🔴 DOCS         Yes   MUST BUILD.
y                 Server           ONLY                 Unlocks
                                                        OS-level
                                                        mounting
                                                        natively.
                                                        (Priority 4)


Interoperabilit   S3-Compatible    ⚪ FUTURE       Yes   COULD
y                 API                                   BUILD. Useful
                                                        for backup
                                                        software
                                                        integration.
Interoperabilit   rclone Crypt     🟡 ADAPTER   Yes   SHOULD
y                 adapter                            BUILD. Ensure
                                                     TelDrive
                                                     indexes rclone
                                                     encrypted
                                                     files.


Interoperabilit   Bidirectional    ⚪ FUTURE    Yes   DO NOT
y                 Sync                               BUILD. Avoid
                                                     rclone bisync
                                                     data loss
                                                     risks24.

Media             Jellyfin Proxy   🟡 ADAPTER   Yes   MUST BUILD.
                  Contract                           Direct HTTP
                                                     streams
                                                     bypassing local
                                                     disk cache.
                                                     (Priority 6)


Media             Subtitle         🟡 PARTIAL   Yes   SHOULD
                  Indexing                           BUILD. High
                                                     value for
                                                     media libraries.


Media             Transcoding      🔴 DOCS      No    DO NOT
                  Engine           ONLY              BUILD.
                                                     Delegate
                                                     entirely to
                                                     Jellyfin4.

Media             Native           ⚪ FUTURE    No    DO NOT
                  TV/Mobile                          BUILD. Focus
                  Apps                               on backend
                                                     API; use
                                                     existing clients.


Search            SQLite FTS5      🟡 PARTIAL   Yes   MUST BUILD.
                  Text Search                        Replaces
                                                     heavy
                                                     RAM-based
                                                      search
                                                      engines9.
                                                      (Priority 7)

Search         Meilisearch/Ela   ⚪ FUTURE       No    DO NOT
               sticsearch                             BUILD.
                                                      Violates
                                                      modest
                                                      hardware
                                                      constraints1.

AI /           Local LLM         🟠              No    EXPERIMENT.
Intelligence   (Ollama)          EXPERIMENTAL         Keep strictly
                                                      isolated as
                                                      optional
                                                      sidecar2.

AI /           Tesseract OCR     🟡 ADAPTER      Yes   SHOULD
Intelligence                                          BUILD.
                                                      Execute
                                                      asynchronousl
                                                      y in
                                                      background
                                                      queues.


AI /           Autonomous        ⚪ FUTURE       N/A   DO NOT
Intelligence   Storage Mgmt                           BUILD. AI must
                                                      never mutate
                                                      production
                                                      data
                                                      independently.


Automation     Cron /            🟢              Yes   Maintain.
               Scheduled         IMPLEMENTED          Essential for
               Jobs                                   internal health
                                                      checks.


Automation     Webhooks /        🔴 DOCS         Yes   SHOULD
               n8n Output        ONLY                 BUILD.
                                                      Delegate
                                                      complex
                                                                                 workflows to
                                                                                 external tools.


M. Top 15 Product Priorities (Ranked)
 1.​ Durable Core Hardening: Finalize and rigorously test the Phase 22 job execution engine.
     (Value: Foundational | Difficulty: Hard | Risk: Low | ₹0: Yes)
 2.​ FloodWait Resilience Subsystem: Implement robust exponential backoff, jitter, and
     strict rate limiting (token-bucket) for all Telegram API interactions to guarantee survival
     against abuse heuristics34. (Value: Critical | Difficulty: Med | Risk: High | ₹0: Yes)
 3.​ Orphaned File Garbage Collection: Resolve the discrepancy between local database
     state and remote Telegram channel state, ensuring deleted files actually free up remote
     quota22. (Value: High | Difficulty: Med | Risk: Low | ₹0: Yes)
 4.​ WebDAV API Implementation: Expose the TelDrive index as a standard WebDAV
     endpoint to achieve global interoperability. (Value: Massive | Difficulty: Hard | Risk: Low |
     ₹0: Yes)
 5.​ Jellyfin Proxy Contract: Create direct, unauthenticated HTTP range-request endpoints
     optimized specifically for Jellyfin streaming, eliminating the need for full VFS caching on
     the host machine. (Value: High | Difficulty: Med | Risk: Low | ₹0: Yes)
 6.​ SQLite FTS5 Integration: Optimize lexical search using FTS5 with WAL journaling,
     ensuring rapid text retrieval without heavy memory footprints9. (Value: High | Difficulty:
     Med | Risk: Low | ₹0: Yes)
 7.​ Immutable Manifests & Snapshots: Guarantee the metadata database acts as the
     ultimate source of truth, enabling full structure recovery even if Telegram channels are
     purged. (Value: High | Difficulty: Hard | Risk: Med | ₹0: Yes)
 8.​ Multi-Token Load Balancing: Abstract Telegram API constraints by distributing chunk
     uploads across a user-provided registry of bot tokens, minimizing per-account throttling.
     (Value: High | Difficulty: Hard | Risk: Med | ₹0: Yes)
 9.​ Rclone VFS Optimization Guidelines: Publish strict, tested configuration profiles for
     rclone mount (mandating caps on --vfs-cache-max-size and --vfs-read-ahead) to
     prevent catastrophic local disk exhaustion during media streaming14. (Value: High |
     Difficulty: Easy | Risk: Low | ₹0: Yes)
 10.​Duplicate Intelligence: Detect redundant files via asynchronous SHA-256 hashing and
     link them in the database rather than re-uploading duplicate bytes to Telegram. (Value:
     Med | Difficulty: Med | Risk: Low | ₹0: Yes)
 11.​REST API for External Automation: Establish comprehensive HTTP endpoints allowing
     external orchestration tools (like n8n) to trigger workflows safely. (Value: Med | Difficulty:
     Med | Risk: Low | ₹0: Yes)
 12.​Local Metadata Extraction: Deploy background workers utilizing ExifTool/ffprobe to
     populate the SQLite database with rich media properties asynchronously. (Value: Med |
     Difficulty: Med | Risk: Low | ₹0: Yes)
 13.​S3-Compatible Gateway: Translate TelDrive structures into an S3-compliant XML/HTTP
      API to attract enterprise backup users. (Value: Med | Difficulty: Hard | Risk: High | ₹0: Yes)
  14.​Cross-Provider Migration Tooling: Develop mechanisms to safely export byte-chunks
      from Telegram directly to local disk arrays or genuine S3 providers, mitigating platform
      lock-in. (Value: Low | Difficulty: Hard | Risk: Med | ₹0: Yes)
  15.​AI-Assisted Tagging (Advisory): Support optional local OCR/Vision pipelines that
      suggest organizational tags, strictly gated pending human or deterministic policy
      approval. (Value: Low | Difficulty: Med | Risk: Med | ₹0: No - Requires specific hardware)
N. DO NOT BUILD List
To fiercely protect the ₹0 budget, maintain architectural sanity, and focus engineering
resources, TelDrive must explicitly refuse to build:
  ●​ A Custom OTT Platform: Do not waste resources building proprietary video players,
       transcoding pipelines, or smart TV applications. Jellyfin solves this natively and infinitely
       better.
  ●​ Virtual File Systems (Native FUSE): Do not attempt to write native C/Go FUSE drivers.
       Rely entirely on users utilizing rclone mount to connect to TelDrive's WebDAV API.
  ●​ Proprietary Encryption: Do not write custom cryptographic chunking. Mandate that
       users requiring encryption wrap TelDrive within an rclone crypt remote.
  ●​ Bidirectional Synchronization: Do not build continuous two-way sync tools. The API
       overhead is massive, and data loss risks are profound. Utilize immutable snapshots
       instead.
  ●​ Autonomous AI Agents: AI must never possess the authority to delete, move, or modify
       primary file structures without deterministic policy gates and user verification.
  ●​ Heavy In-Memory Search Engines: Do not integrate or mandate Meilisearch or
       Elasticsearch. Their virtual memory requirements violate the target hardware envelope of
       modest personal servers.
  ●​ Visual Workflow Editors: Do not build custom UI flowchart tools for automation routing.
       Expose webhooks and let n8n handle visual logic.
O. Recommended Architecture
The ideal final architecture establishes strict boundaries, separating the control plane from the
data plane and ensuring modularity, safety, and delegation.
 Responsibility       TelDrive            rclone              Jellyfin             External /
                                                                                   Optional


 Storage              Owns                Connects            N/A                  N/A
 Abstraction          metadata, API,      WebDAV to OS
                      WebDAV              (FUSE)


 Byte Transfer        Owns MTProto        Handles             N/A                  S3/Local
                      / Bot API           external
                    chunking           sync/copy                            (Backend)


 Metadata &         Owns SQLite        N/A               N/A                N/A
 Indexing           database &
                    FTS5


 Media              Proxies            N/A               Owns UI &          N/A
 Library/Playba     byte-range                           Playback
 ck                 requests


 Transcoding        N/A                N/A               Owns               N/A
                                                         hardware
                                                         rendering


 Search             Owns local         N/A               N/A                Meilisearch
                    lexical/metadat                                         (Strictly
                    a search                                                Optional)


 Artificial         Owns               N/A               N/A                Ollama/Whisp
 Intelligence       deterministic                                           er (Sidecar)
                    approval gates


 Automation /       Owns internal      N/A               N/A                n8n / Home
 Snapshots          cron, GC,                                               Assistant
                    manifests



P. Product Evolution
The roadmap must transition from foundational stability to universal interoperability before
attempting advanced intelligence features.
   ●​ Stage 1 — Foundation (Current Status): Establishing the durable jobs engine, basic file
      tracking, SQLite schemas, and deterministic safety boundaries.
   ●​ Stage 2 — Interoperability (Immediate Focus): Building the WebDAV server and
      comprehensive REST API. Guaranteeing flawless rclone integration via standard
      protocols.
   ●​ Stage 3 — Resilience: Implementing multi-token load balancing and aggressive MTProto
      FloodWait handling to secure the Telegram dependency against abuse heuristics.
   ●​ Stage 4 — Media Delegation: Finalizing the read-only HTTP contract for Jellyfin,
      optimizing byte-range requests to support instant video seeking without caching entire
      files locally.
  ●​ Stage 5 — Intelligence (Deterministic): Implementing SQLite FTS5 for zero-cost
     search, asynchronous deduplication, and fixing orphaned file garbage collection to
     maintain storage hygiene.
  ●​ Stage 6 — Intelligence (AI): Introducing optional, hardware-dependent isolated workers
     (Ollama, OCR) strictly as advisory sidecars that feed recommendations back to the
     control plane.
  ●​ Stage 7 — Automation Ecosystem: Exposing webhooks and event triggers to allow n8n
     and external cron systems to command the storage plane.
  ●​ Stage 8 — Provider Independence: Building seamless, one-click migration tools to
     export byte-chunks off Telegram onto enterprise S3 or local arrays, fulfilling the promise
     of true data ownership.
Q. Biggest Risks
The project faces several existential architectural risks that must be continuously mitigated:
  1.​ The Telegram Dependency Trap: Telegram is actively and aggressively combating
      infrastructure abuse. If TelDrive assumes Telegram is functionally "unlimited" and
      encourages users to upload multi-terabyte media libraries via aggressive parallel
      connections, it will inevitably result in mass account bans and catastrophic data loss33.
      TelDrive must enforce strict rate limits, utilize backoff algorithms, and explicitly warn
      users of the operational envelope.
  2.​ VFS Cache Disk Exhaustion: By relying on rclone for FUSE mounting—which is the
      correct architectural choice—aggressive media streaming will rapidly fill the host
      machine's local disk due to chunk caching and read-ahead buffering39. TelDrive must
      mitigate this by providing explicit, tested configuration profiles (e.g., capping
      --vfs-cache-max-size) to protect users from crashing their own servers14.
  3.​ Scope Explosion (The OTT Trap): Diverting precious, zero-cost engineering resources
      to build a sleek media player user interface, implement transcoding, or manage watch
      histories will stall the development of core storage stability. Jellyfin already dominates
      this space; competing with it is a critical error.
  4.​ Hardware Incompatibility via AI: Mandating AI embeddings, natural language planning,
      and video metadata extraction demands high CPU/GPU and RAM overhead2. Treating
      these as core, synchronous features alienates the primary demographic: users running
      modest hardware, Raspberry Pis, or cheap VPS instances.
R. Final Verdict
If responsible for the strategic direction of TelDrive, I would immediately abandon all
conceptual aspirations of building an Over-The-Top (OTT) media platform, a unified personal
data suite, or a fully autonomous AI storage manager.
The most powerful, defensible, and sustainable product identity for TelDrive is an Intelligent
Storage Operating System—a headless, API-first control plane that abstracts the chaos, rate
limits, and unreliability of Telegram into standard, highly resilient WebDAV and REST interfaces.
I would relentlessly focus engineering efforts on hardening the Telegram upload/download
pipeline to survive 420 FLOOD_WAIT restrictions via robust connection pooling, fixing the
database-to-channel state mismatches that generate orphaned files, and guaranteeing fast,
seamless read-only streaming to Jellyfin via native HTTP range requests. I would explicitly
refuse to build real-time transcoding, native smart TV media clients, bidirectional sync engines,
or mandatory heavy AI features, permanently delegating those workloads to Jellyfin, rclone,
and optional local sidecar containers.
By treating Telegram as a hostile, heavily metered, but ultimately useful byte-substrate—rather
than a limitless utopian hard drive—TelDrive can deliver a robust, zero-cost personal data fabric
that survives long after conventional, reckless Telegram abuse-scripts are banned and
forgotten.

Works cited

  1.​ Squeezing millions of documents in 128 TB of virtual memory,
       https://www.meilisearch.com/blog/dynamic-virtual-address-management
  2.​ Ollama Hardware Requirements: RAM, VRAM and GPU - DevToolHub,
       https://devtoolhub.com/ollama-hardware-requirements/
  3.​ Projects in Awesome Lists tagged with plex-media-server,
       https://awesome.ecosyste.ms/projects?keyword=plex-media-server&page=2&pe
       r_page=100
  4.​ Transcoding | Jellyfin, https://jellyfin.org/docs/general/post-install/transcoding/
  5.​ rclone with S3-Compatible Storage: The Complete Guide (2026),
       https://danubedata.ro/blog/rclone-s3-compatible-storage-complete-guide-2026
  6.​ Rclone Seedbox Guide: Setup, Features & Best Providers 2026,
       https://www.rapidseedbox.com/blog/rclone-seedbox
  7.​ Rclone for 2025: Sync and Backup to Google Drive, S3, and Wasabi,
       https://mangohost.net/blog/rclone-for-2025-sync-and-backup-to-google-drive-
       s3-and-wasabi/
  8.​ Ollama System Requirements: 8GB RAM Minimum, No GPU Needed,
       https://localaimaster.com/blog/ollama-system-requirements
  9.​ How to Fix Slow SQLite Queries - DB Pro Blog,
       https://www.dbpro.app/blog/how-to-fix-slow-sqlite-queries
  10.​来尝试无限容量，可以webdav挂载的teldrive吧！,
       https://www.voidval.com/archives/teldrive-deployment/
  11.​ Teldrive, 안드로이드 기기에서 스트리밍 활용,
       https://singingdalong.blogspot.com/2025/02/Teldrive-streaming-service-on-Andr
       oid-.html
  12.​5th mode: --vfs-cache-mode off+buffered to ram · Issue #6027 - GitHub,
       https://github.com/rclone/rclone/issues/6027
  13.​Feature: --vfs-cache-max-size behave as --cache-chunk-total-size,
       https://forum.rclone.org/t/feature-vfs-cache-max-size-behave-as-cache-chunk-t
       otal-size/33559
  14.​Fix VFS Cache Disk Full Errors — Manage Mount ... - RcloneView,
       https://rcloneview.com/support/blog/fix-vfs-cache-disk-full-errors-rcloneview
  15.​Jellyfin docker can't write to truenas folder. Sqlite database locked,
    https://www.truenas.com/community/threads/jellyfin-docker-cant-write-to-truen
    as-folder-sqlite-database-locked.110092/
16.​Rclone mount with vfs cache mode full is using up local ... - Reddit,
    https://www.reddit.com/r/rclone/comments/xnbhsx/rclone_mount_with_vfs_cache
    _mode_full_is_using_up/
17.​Rclone fails to control disk usage and it's filling the disk to 100%,
    https://forum.rclone.org/t/rclone-fails-to-control-disk-usage-and-its-filling-the-d
    isk-to-100/41494/4
18.​Rclone fails to control disk usage and it's filling the disk to 100%,
    https://forum.rclone.org/t/rclone-fails-to-control-disk-usage-and-its-filling-the-d
    isk-to-100/41494
19.​This cloud trick gives you unlimited photo storage for free - MakeUseOf,
    https://www.makeuseof.com/cloud-trick-gives-unlimited-photo-storage-free/
20.​Telegram Mobile Proxies - Automation & Scraping,
    https://mobileproxies.org/solutions/telegram
21.​[feat] allow disabling deletion of files #452 - tgdrive/teldrive - GitHub,
    https://github.com/tgdrive/teldrive/issues/452
22.​[Bug]: Orphaned Telegram channel messages persist despite,
    https://github.com/tgdrive/teldrive/issues/483
23.​Bisync - Rclone, https://rclone.org/bisync/
24.​Bisync should be considered experimental · Issue #6082 - GitHub,
    https://github.com/rclone/rclone/issues/6082
25.​FAQ | TeleSender Documentation, https://tele-sender.com/docs/faq/
26.​Pyrogram Python fails to catch Exception - telegram - Stack Overflow,
    https://stackoverflow.com/questions/76618298/pyrogram-python-fails-to-catch-e
    xception
27.​GitHub - tgdrive/teldrive, https://github.com/tgdrive/teldrive
28.​Telegram Premium Features: A Creator's Guide to What's Included,
    https://www.brandghost.ai/blog/posts/telegram-premium-features-creators
29.​Advanced Features and Telegram Premium Perks - Affiliate Dragons,
    https://affdragons.com/telegram-usage-guide-advanced-features-and-telegram
    -premium-perks/
30.​Telegram Limits — Telegram Info, https://limits.tginfo.me/en
31.​OpenClaw Telegram Integration: Complete Setup Guide 2026,
    https://extuitive.com/articles/openclaw-telegram-integration
32.​Telegram Limits — Telegram Info, https://limits.tginfo.me/
33.​are there any cloud storage services that allow you to store pirated,
    https://www.reddit.com/r/Piracy/comments/1ukiht2/are_there_any_cloud_storage_
    services_that_allow/
34.​GitHub - gurveeer/TG-DL-BOT: A powerful Telegram bot built with,
    https://github.com/gurveeer/TG-DL-BOT
35.​Telethon API Documentation Overview | PDF | Proxy Server - Scribd,
    https://www.scribd.com/document/728599913/telethon
36.​td/ARCHITECTURE.md at main · gotd/td - GitHub,
    https://github.com/gotd/td/blob/main/ARCHITECTURE.md
37.​Amazon S3 Storage Providers - Rclone, https://rclone.org/s3/
38.​Rclone, https://rclone.org/
39.​rclone serve sftp, https://rclone.org/commands/rclone_serve_sftp/
40.​rclone mount, https://rclone.org/commands/rclone_mount/
41.​Can rclone act as an encrypted WebDAV proxy (WebDAV → live,
    https://forum.rclone.org/t/can-rclone-act-as-an-encrypted-webdav-proxy-webd
    av-live-encrypt-decrypt-webdav/53532
42.​Using Jellyfin with rclone mounted Google Drive causes data to not,
    https://www.reddit.com/r/jellyfin/comments/l7vk01/using_ jellyfin_with_rclone_mo
    unted_google_drive/
43.​Ollama on Ubuntu: From CPU Pain to GPU Gain - DZone,
    https://dzone.com/articles/ollama-ubuntu-local-llm-setup
44.​A Deep Dive into Meilisearch Internals, Vector Retrieval, and Algolia,
    https://medium.com/towardsdev/architecting-search-engines-a-deep-dive-into-
    meilisearch-internals-vector-retrieval-and-algolia-92779f29488e
45.​Massive document addition causes freeze · Issue #5958 - GitHub,
    https://github.com/meilisearch/meilisearch/issues/5958
46.​Meilisearch vs Typesense | Alternative Comparison,
    https://www.meilisearch.com/comparisons/meilisearch-vs-typesense
47.​Comprehensive SQLite cheatsheet covering database ... - GitHub,
    https://github.com/cheatnotes/sqlite-cheatsheet
48.​SQLite Performance Tips for Web Applications - DEV Community,
    https://dev.to/ahmet_gedik778845/sqlite-performance-tips-for-web-applications
    -29o3
49.​How We Built a Universal Swagger → MCP Server Converter,
    https://medium.com/@bad.vano/how-we-built-a-universal-swagger-mcp-server
    -converter-solving-the-ai-context-window-problem-for-0294063b1e0f
50.​Cache, Read Ahead, and VFS Settings for Smooth Cloud Drives,
    https://rcloneview.com/support/blog/mount-performance-tuning-rcloneview
