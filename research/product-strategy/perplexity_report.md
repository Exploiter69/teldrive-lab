TelDrive Product Strategy Research
A. Executive Summary
TelDrive should not become a Telegram-backed OTT, Dropbox clone, or general-purpose
replacement for Nextcloud. Its strongest identity is:
       A provider-agnostic personal storage control plane that can use Telegram as one
       storage backend, with durable transfers, verification, archive workflows, search, and
       integrations with mature systems such as rclone and Jellyfin.
Telegram is useful because it can provide inexpensive remote storage and convenient access,
but it is not a reliable storage contract. Its practical limits, undocumented throttling, account
dependence, inactive-account deletion, channel-history constraints, and operational instability
make “unlimited Telegram cloud” an unsafe architectural assumption. Telegram should be
treated as an optional but important provider, not TelDrive’s permanent identity.
The completed Phase 0–22 foundation appears technically ambitious and valuable, but it is
currently closer to a control-plane framework than a finished end-user product. The next work
should focus on productization, provider abstraction, operational reliability, and a narrow set
of high-value workflows—not additional experimental intelligence or a custom media platform.

B. Product Identity

Recommended identity
       TelDrive: a safe, auditable storage operating layer for personal archives, backups, and
       media—Telegram-compatible, rclone-native, and provider-independent.
This is stronger than “Telegram Drive” for five reasons:
  1. It preserves TelDrive’s existing engineering investment.
  2. It creates value even if Telegram changes its policies.
  3. It avoids competing directly with mature products such as Nextcloud, Seafile, and Jellyfin.
  4. It makes rclone, local disks, WebDAV, S3, and future providers first-class options.
  5. It supports storage, media, documents, backups, and automation without forcing TelDrive
     to own every client experience.
What TelDrive should not claim
It should not promise:
     Unlimited storage.
     Unlimited throughput.
     Dropbox-like synchronization.
     Production-grade NAS semantics.
     Reliable low-latency media streaming from Telegram.
     A complete Netflix-like OTT experience.
     Disaster-proof backups using Telegram alone.
     Enterprise multi-user collaboration.
     Autonomous AI storage management.

C. Core Product Pillars
               Pillar                                           Purpose                                  Recommendation

  Provider-independent storage   Manage local, Telegram, rclone, WebDAV, S3, and other backends
                                                                                                        Must build
  control                        through one policy layer

  Durable transfer and archive   Resume, retry, verify, snapshot, restore, retention, and audit
                                                                                                        Must build
  workflows                      operations

                                 Organize documents, photos, media, backups, and long-term
  Personal digital archive                                                                              Must build
                                 records

                                 Make TelDrive usable by rclone, HTTP clients, Jellyfin, scripts, and
  Interoperability                                                                                      Must build
                                 automation tools

  Deterministic search and       Search filenames, metadata, text, OCR, transcripts, and media          Must build
  indexing                       attributes                                                             selectively

                                 Feed Jellyfin and similar systems without rebuilding their playback
  Media integration                                                                                     Should build
                                 stack

                                 Scheduled jobs, triggers, notifications, and policy-controlled
  Safe automation                                                                                       Should build
                                 workflows

                                 Recommendations, duplicate explanations, classification, and
  Advisory intelligence                                                                                 Later, optional
                                 natural-language assistance

The core differentiator is not Telegram access alone. It is the combination of durability,
verification, provider abstraction, and orchestration around unreliable or heterogeneous
storage.
D. Real-World Ecosystem Findings
TelDrive and Telegram storage
The open-source TelDrive ecosystem consistently frames TelDrive as a wrapper around
Telegram storage with rclone compatibility. Its implementation pattern is generally:
 1. Split files into chunks.
 2. Upload chunks as Telegram messages in a configured channel or group.
 3. Maintain metadata in a database.
 4. Expose files through a web interface and/or rclone backend.
 5. Reconstruct files for downloads and external applications.
The existence of multiple forks and related projects shows genuine demand, but also
fragmentation. Examples include TelDrive forks, independent Telegram rclone backends,
Telegram-to-cloud ingestion tools, and projects that use Telegram as a remote storage layer. The
recurring user motivations are:
    Avoiding paid cloud storage.
    Storing large personal media libraries.
    Accessing files through rclone.
    Using Telegram’s existing cross-device availability.
    Building personal archives with minimal infrastructure.
    Moving files between Telegram, local disks, and other cloud providers.
However, reported issues expose the weaknesses of this model:
    Large uploads can become extremely slow or unreliable.
    Repeated downloads may fail or trigger quota-related behavior.
    Orphaned channel messages can remain after metadata restoration or cleanup.
    Authentication/session persistence can fail.
    Media-server access through rclone can be much slower than the TelDrive web UI.
    Large channel histories are difficult to enumerate; one reported issue describes access
    problems beyond approximately one million messages, but this should be treated as an
    observed implementation/platform constraint rather than a universal official Telegram
    limit. [1] [2] [3] [4]

Product implication
TelDrive should productize the problems users repeatedly encounter:
    resumable transfers;
    local metadata independent of Telegram listings;
    manifest-based recovery;
    explicit rate control;
    bounded concurrency;
    cache-aware reads;
    provider health scoring;
    export and migration;
    verification after every important operation.
It should not merely add another Telegram file browser.

Telegram plus rclone
rclone already provides a large amount of functionality TelDrive should not recreate:
    copying;
    moving;
    syncing;
    bidirectional sync;
    mounting;
    filtering;
    checksums;
    deduplication workflows;
    retries;
    bandwidth limits;
    encryption wrappers;
    remote control;
    support for local, WebDAV, S3, HTTP, and many other backends.
The official command documentation explicitly includes bisync, dedupe, and mount. TelDrive’s
job is to provide a robust provider adapter and higher-level policy—not to implement another
general-purpose copy engine. [5]
The most valuable TelDrive/rclone integration is:

  TelDrive policy and metadata
          ↓
  TelDrive provider adapter
          ↓
  rclone-compatible remote
          ↓
  local files, Jellyfin, scripts, backup tools, and automation
Telegram plus media servers
The practical pattern is to mount TelDrive through rclone and point Jellyfin, Plex, or Emby at
that mounted filesystem. TelDrive documentation and community reports describe Docker
volume and rclone-based media-server integration. [6]
This can work for:
    occasional personal playback;
    direct-play media;
    small libraries;
    low-concurrency users;
    cached or recently accessed content.
It is a poor foundation for:
    several concurrent viewers;
    frequent seeking;
    image-heavy library scans;
    transcoding from remote Telegram data;
    thousands of small files;
    always-on media-server workloads.
Jellyfin itself recommends local database storage and notes that cloud-backed filesystems can
be used through rclone, but it warns that image extraction may require downloading entire
files. Jellyfin’s design goal is direct play; incompatible media may require direct streaming or
transcoding, with subtitle burn-in among the more expensive cases. [7] [8] [9]

Recommendation
Integrate with Jellyfin, but make the integration storage-aware:
    local metadata and thumbnails;
    delayed or bounded library scans;
    prefetch for selected media;
    explicit cache sizing;
    no automatic full-library extraction from Telegram;
    direct-play-first guidance;
    health and latency warnings.
Telegram ingestion and backup workflows
A recurring pattern is:

  Telegram channel/group
      → user session listener
      → local temporary storage
      → rclone upload
      → checksum verification
      → optional deletion


This is useful for:
    receiving media from mobile devices;
    moving files from Telegram to local or cloud storage;
    importing documents;
    download-manager workflows;
    archival pipelines.
Projects exist that monitor Telegram channels, download new content, send it through rclone,
and delete temporary files after success. [10]
TelDrive should support this through an event-driven ingestion adapter, not as an all-purpose
download platform. The adapter should have:
    idempotency keys;
    message IDs;
    content hashes;
    retry state;
    quarantine;
    retention policy;
    verification;
    deletion only after confirmed destination integrity.

Telegram as “free unlimited cloud”
Telegram’s appeal is obvious, but “unlimited” is not an operational guarantee. Telegram’s FAQ
states that inactive accounts are deleted after a configurable period, with 18 months as the
default, and that account deletion removes cloud data. [11] [12]
This alone disqualifies an account-only Telegram setup as a sole archival authority.
E. Telegram Capacity and Risk Report
Documented constraints
Telegram’s official Bot API distinguishes between:
    files already stored on Telegram and reused by file_id;
    URL-based sending;
    multipart uploads.
The Bot API documents 2,000 MB uploads for bots through the relevant API path, while
ordinary multipart uploads have lower limits depending on the operation. [13]
The MTProto file API documents upload-part behavior and indicates that upload limits depend
on the maximum number of file parts and part size. It also documents speed-related behavior
such as FLOOD_PREMIUM_WAIT_X. [14] [15]
Telegram’s official terms prohibit spam, scams, illegal content, and other abusive use.
Violations may result in temporary or permanent bans. [16]
Telegram does not publish a complete, stable quota and throughput contract for using private
channels as a high-volume object store.

Community and implementation observations
Observed TelDrive issues report:
    uploads above roughly 200 MB becoming difficult in some environments;
    large movie uploads taking a long time;
    retries causing repeated downloads;
    connection failures around very large chunks;
    difficulty bypassing the effective non-Premium per-file limit;
    orphaned messages after database restoration;
    channel-history access problems at very large message counts;
    performance problems when media servers access TelDrive through rclone. [2] [3] [4] [17] [18]
These are not universal thresholds. They demonstrate variability and risk.

Unknowns
The following should be treated as unknown or dynamic:
    sustainable per-account upload throughput;
    sustainable continuous download throughput;
    per-channel message creation rate;
    exact concurrent transfer limits;
    exact thresholds for flood waits;
    how account age, geography, trust signals, client type, and traffic pattern affect throttling;
    whether Telegram will retain current storage behavior permanently;
    whether large archives remain equally accessible over long periods;
    whether future API or policy changes will affect user sessions, channels, or file retrieval.
The correct engineering response is not to discover “safe bypass numbers.” It is to design
around backpressure and failure.

Sustainable operating envelope
A responsible personal system can reasonably use Telegram for:
    low-to-moderate volume personal archives;
    intermittent backups;
    selected media libraries;
    documents and photos;
    asynchronous ingestion;
    cold or warm storage;
    one or a few users;
    bounded concurrency;
    long-running jobs that tolerate pauses;
    verified replicas elsewhere.
A safe design should assume:
    uploads can pause for minutes or longer;
    downloads can fail and resume later;
    flood waits are normal events;
    large files may require chunking and multiple retries;
    Telegram is unavailable occasionally;
    indexes must remain usable without live Telegram listing;
    restoration may require provider repair or re-authentication.

Aggressive but potentially viable envelope
This may work but should be explicitly labeled operationally risky:
    multi-terabyte archives;
    continuous background uploads;
    large media libraries;
    several simultaneous transfers;
    automated channel ingestion;
    repeated media-server access;
    frequent rescans;
    high-volume file creation;
    sustained re-fetching of cold data.
The system should not silently operate here. It needs:
    rate budgets;
    queue priority;
    concurrency limits;
    circuit breakers;
    per-provider health state;
    local cache;
    transfer pausing;
    operator alerts;
    export tests;
    alternate copy requirements.

Red zone
TelDrive should not design around:
    millions of small files as if Telegram were a normal filesystem;
    high-concurrency media streaming;
    constant random seeking over remote Telegram data;
    full-library rescans every day;
    continuous bulk upload at the maximum available speed;
    repeated re-downloads without local caching;
    treating message history as a reliable index;
    using a single Telegram account as the only copy;
    building a public multi-user storage service on top of a personal account;
    assuming a channel will remain accessible forever.

Absolute no-go behavior
TelDrive must not support or encourage:
    account farms;
    ban evasion;
    flood-limit evasion;
    proxy rotation designed to avoid enforcement;
    spam or unsolicited distribution;
    prohibited content;
    deceptive automation;
    exploiting Telegram behavior as a substitute for a paid storage contract.

Core conclusion
Telegram must be treated as:
       An unreliable external storage substrate with useful economics, not an effectively
       unlimited storage backend.

F. Telegram Dependency Recommendation
Telegram should be:
    a major supported provider;
    an optional product entry point;
    a provider with a first-class adapter;
    replaceable by local storage, WebDAV, S3, or other rclone-compatible backends.
Telegram should not be TelDrive’s only identity.
The architecture should define a provider interface containing:
    object or file identity;
    upload;
    download;
    range or chunk retrieval;
    listing;
    metadata;
    delete;
    checksum evidence;
    resumability;
    capability discovery;
    rate/backpressure status;
    provider-specific error classification.
Every important object should have a provider-independent manifest containing:
    stable TelDrive ID;
    logical path;
    size;
    SHA-256;
    chunk map;
    provider object/message references;
    creation and modification dates;
    encryption state;
    verification state;
    replica state;
    lifecycle policy.

Failure survival
If Telegram introduces restrictions, TelDrive should survive through:
 1. Pausing Telegram jobs.
 2. Keeping metadata and manifests locally.
 3. Continuing to serve cached content.
 4. Exporting manifests and provider references.
 5. Copying verified content to another provider.
 6. Supporting provider reassignment.
 7. Rebuilding remote indexes from manifests instead of relying solely on Telegram history.
 8. Reporting degraded availability clearly.
 9. Offering a migration plan rather than pretending the provider is healthy.
The product should include a provider evacuation command early, not after a disaster.

G. rclone Strategy
Use rclone for
                   Capability                                            Decision
       Remote abstraction             Use rclone

       Copy/move/sync                 Use rclone

       Bisync                         Use rclone

       Mounting                       Use rclone carefully

       Filtering                      Use rclone

       Retry and bandwidth controls   Use rclone, augmented by TelDrive policy

       Checksums                      Use rclone where supported, verify independently where needed

       WebDAV/S3/HTTP access          Use rclone adapters where appropriate
                 Capability                                               Decision

       Encryption wrapper             Support rclone crypt, but retain TelDrive’s own manifest-aware encryption options

       Remote control                 Integrate selectively

       General file-transfer engine   Do not rebuild


TelDrive must own
    authorization;
    policy;
    durable job state;
    workflow dependencies;
    provider capability modeling;
    manifests;
    archive semantics;
    snapshots;
    retention;
    verification evidence;
    rollback and restore plans;
    safety boundaries;
    audit history;
    storage intelligence;
    provider evacuation;
    user-facing explanations.
A useful rule:
       If the feature is about moving bytes, prefer rclone. If it is about deciding what should
       happen, proving what happened, or recovering from failure, TelDrive should own it.

Important rclone limitation
A mounted remote is not equivalent to a local filesystem. Media servers, databases, editors, and
applications that expect low-latency random access may behave poorly. TelDrive must expose
mount modes and warnings:
    cold remote;
    cached remote;
    read-only media mode;
    archive mode;
    local materialization mode.
H. OTT Decision
Comparison
       Option                     Benefits                               Problems                           Verdict

                                                       Huge scope: metadata, playback, clients,
  Build complete
                      Full product control             auth, profiles, transcoding, TV apps, mobile,   Reject
  OTT
                                                       casting, history, recommendations

                      Mature media library, clients,
  TelDrive plus                                        Integration and remote-storage performance
                      playback, subtitles, users,                                                      Recommended
  Jellyfin                                             challenges
                      transcoding

  Custom
                      Narrow scope and TelDrive        Rebuilds playback and client complexity;        Only as a later
  lightweight
                      branding                         weak device ecosystem                           companion
  media client

                      Jellyfin for serious media,
                                                                                                       Recommended
  Hybrid              TelDrive UI for                  More integration work but preserves scope
                                                                                                       long-term
                      files/archive/search


Recommendation: hybrid, Jellyfin-first
TelDrive should provide:
     a stable filesystem/API backend;
     media discovery and metadata exports;
     prefetch/materialization;
     health and latency information;
     optional Jellyfin setup;
     a plugin or integration layer where useful;
     lightweight browsing for quick previews and files.
Jellyfin should own:
     media library presentation;
     playback;
     user profiles;
     watch history;
     continue watching;
     subtitles and audio selection;
     transcoding;
     clients;
     TV and mobile experiences.
Jellyfin is explicitly designed as a free software media system with multiple clients, and its
official documentation covers direct play, streaming, transcoding, and hardware acceleration.
Rebuilding that ecosystem would be strategically irrational. [8] [19] [20]

Media constraints
TelDrive should optimize for:
       direct play;
       locally cached metadata;
       pre-generated thumbnails;
       local or materialized media for frequently watched content;
       optional hardware acceleration through Jellyfin;
       no promise that Telegram-backed cold media behaves like a local NAS.
A modest Linux machine can run Jellyfin for direct play and light workloads. CPU-only
transcoding should be considered optional and limited. Hardware acceleration is available for
supported Intel, AMD, Nvidia, Apple, and Rockchip hardware, but that is hardware-dependent.
[20] [21]


I. WebDAV and Interoperability Strategy
            Interface                    Priority                                         Decision
  REST API                                  Core     TelDrive should own

  rclone remote                             Core     TelDrive should maintain

  HTTP downloads/uploads                    Core     TelDrive should own, with range support

  WebDAV                              Important      Expose through a mature adapter or a deliberately limited implementation

  S3                             Important later     Prefer an adapter or gateway; do not build a full S3 server initially

  FUSE                                   Adapter     Use rclone or existing filesystem mechanisms

  SMB                       Do not build initially   Use OS-level sharing around a local materialized/cache path

  NFS                               Do not build     Not appropriate for Telegram-backed remote storage

  Docker volume                Optional adapter      Useful for Jellyfin and containers

  Local filesystem export                   Core     Materialize or cache explicitly


WebDAV recommendation
WebDAV is valuable because it connects to existing file managers and applications. Nextcloud
demonstrates the practical value of WebDAV for desktop and filesystem access. [22]
However, WebDAV should not become a second independent storage engine. TelDrive should
expose a conservative, authenticated, rate-limited WebDAV layer or delegate it to a mature
gateway backed by TelDrive’s REST/API layer.
The first WebDAV version should support:
    read;
    write;
    move;
    copy;
    delete;
    directory listing;
    range downloads;
    authentication;
    explicit consistency semantics.
It should not promise perfect filesystem behavior over Telegram.

J. Search and Data Intelligence
Search architecture
Use a layered, deterministic-first architecture:
  1. SQLite metadata database.
  2. Indexed filename and path search.
  3. Structured metadata filters.
  4. Full-text search using SQLite FTS5 or Tantivy if scale requires it.
  5. OCR and transcript fields.
  6. Media metadata and subtitle indexes.
  7. Optional embeddings.
  8. Natural-language interpretation over deterministic retrieval.
Avoid introducing Elasticsearch/OpenSearch for a personal installation. The operational
burden is unjustified at zero cost and modest hardware.

What should be deterministic
    object identity;
    paths;
    checksums;
    duplicate groups;
    size;
    timestamps;
    media technical metadata;
    OCR text;
    transcript text;
    search ranking primitives;
    integrity state;
    retention decisions;
    authorization;
    restore plans.

What AI may assist with
    explaining duplicate groups;
    suggesting archive categories;
    classifying ambiguous files;
    extracting semantic queries;
    recommending likely relevant documents;
    summarizing transcripts;
    proposing metadata corrections;
    explaining storage growth;
    generating a workflow plan for review.

What AI must not decide alone
    delete;
    overwrite;
    purge;
    restore over an existing path;
    change retention;
    change encryption;
    expose private files;
    migrate the only copy;
    authorize a destructive workflow.

K. AI Strategy
The appropriate boundary is Level 3 moving carefully toward Level 4:

  AI proposes
  → deterministic policy validates
  → user or pre-approved policy authorizes
  → durable executor mutates
  → verification proves result
  → audit records evidence


High-value AI
     natural-language search over deterministic indexes;
     archive recommendations;
     duplicate explanations;
     media/document classification;
     OCR/transcript summarization;
     “why is storage growing?” explanations;
     workflow drafting;
     anomaly explanations.

Low-value or dangerous AI
     autonomous cleanup;
     free-form file organization without preview;
     automatic retention changes;
     unconstrained media metadata rewriting;
     “AI decides what is important” deletion;
     mandatory cloud AI APIs;
     AI-generated embeddings for every file by default.
Local runtimes such as Ollama or llama.cpp can be optional. They should not be required for
core functionality because CPU inference can be slow and model availability varies.

L. Product Completeness Matrix
The matrix below distinguishes the stated Phase 0–22 foundation from broader product
capabilities. “Implemented + tested” means the project context explicitly says the capability
was host-tested or verified; it does not independently prove production maturity.

        Feature             Category        Current state           Value    Risk           Action
                         🟢 Implemented
  Project architecture                   Foundation exists     High         Low      Maintain
                         + tested

                         🟢 Implemented
  Configuration                          Foundation exists     High         Low      Maintain
                         + tested

                         🟢 Implemented
  Local metadata                         Foundation exists     High         Medium   Harden migrations
                         + tested

                         🟢 Implemented   Explicit boundaries
  Safety boundaries                                            Critical     Low      Preserve
                         + tested        exist
      Feature           Category          Current state           Value    Risk            Action

                     🟢 Implemented
Audit logging                         Audit history exists   High         Low      Add export
                     + tested

Deterministic        🟢 Implemented    Core principle
                                                             Critical     Low      Preserve
behavior             + tested         implemented

                     🟢 Implemented    Transfer workflow                            Improve provider
Upload                                                       Critical     High
                     + tested         exists                                       abstraction

                     🟢 Implemented    Transfer workflow                            Add cache and range
Download                                                     Critical     High
                     + tested         exists                                       policy

                                      Transfer and                                 Validate across
Copy/move            🟢 Implemented                           High         Medium
                                      organization support                         providers

                                      Likely
                                                                                   Require
Rename/delete        🟢 Implemented    metadata/provider      High         High
                                                                                   confirmations
                                      operations

                                                                                   Clarify provider
Folders              🟢 Implemented    Logical organization   High         Medium
                                                                                   semantics

                     🟢 Implemented                                                 Keep provider-
Checksums                             SHA-256 evidence       Critical     Low
                     + tested                                                      independent

                     🟢 Implemented    Duplicate                                    Improve
Duplicate grouping                                           High         Medium
                     + tested         intelligence exists                          explainability

Deduplication        🟡 Adapter /      Report-only                                  Keep report-only
                                                             Medium       High
mutation             contract         concepts noted                               initially

CAS                  🟠 Experimental   Conceptual             Low/Medium   High     Do not prioritize

                     🟢 Implemented    Plans and
Archive plans                                                High         Medium   Productize UI
                     + tested         authorization exist

                     🟢 Implemented    No-overwrite restore
Restore                                                      Critical     High     Add disaster drills
                     + tested         exists

                     🟢 Implemented    Incremental
Snapshots                                                    Critical     Medium   Add export/import
                     + tested         snapshots exist

                     🟢 Implemented
Retention                             Retention exists       High         High     Add simulation mode
                     + tested

                     🟢 Implemented                                                 Add provider
Backup jobs                           Durable jobs exist     Critical     Medium
                     + tested                                                      evacuation

                     🟡 Adapter /      Underlying system
Telegram backend                                             Critical     High     Isolate dependency
                     contract         exists

                                      Configured storage
Telegram channels    🟢 Implemented                           High         High     Add capability checks
                                      destination

                     🟡 Adapter /      Possible provider                            Support only if
Telegram groups                                              Medium       High
                     contract         path                                         necessary

Telegram user                         User-session
                     🟢 Implemented                           High         High     Secure sessions
account                               workflows exist
       Feature         Category         Current state           Value    Risk            Action

Telegram bot        🟡 Adapter /     Bot API differs                              Do not treat as
                                                           Medium       High
account             contract        materially                                   equivalent

                                    Core TelDrive
File retrieval      🟢 Implemented                          Critical     High     Add caching
                                    behavior

                                    Retry/failure
Rate handling       🟢 Implemented                          Critical     High     Add adaptive budgets
                                    foundation exists

                                    Requires provider-
Flood handling      🟡 Partial                              Critical     High     Must improve
                                    aware queueing

                                    Needed for media
Caching             🟡 Partial                              Critical     High     Prioritize
                                    and retries

                                    Backup manifests
Manifests           🟢 Implemented                          Critical     Medium   Make universal
                                    exist

                                    Existing                                     Treat as compatibility
rclone remote       🟢 Implemented                          Critical     Medium
                                    compatibility                                contract

rclone copy/sync    🟢 Delegated     rclone owns it         Critical     Low      Do not rebuild

rclone mount        🟢 Delegated     rclone owns it         High         High     Document limitations

rclone bisync       🟢 Delegated     rclone owns it         Medium       High     Do not duplicate

rclone check        🟢 Delegated     rclone owns it         High         Low      Integrate results

                                    rclone owns basic                            Keep TelDrive
rclone dedupe       🟢 Delegated                            Medium       Medium
                                    command                                      reporting

                    🟢 Delegated /                                                Document key
rclone crypt                        Existing option        High         Medium
                    optional                                                     management

                    🟢 Delegated +
Bandwidth limits                    rclone supports it     High         Low      Add TelDrive budgets
                    policy

rclone remote
                    🟡 Adapter       Possible integration   Medium       Medium   Optional
control

                    🟢 Implemented   Discovery capability
Media discovery                                            High         Medium   Stabilize schemas
                    + tested        exists

Video/audio/image                   Probing capability
                    🟢 Implemented                          High         Medium   Avoid full rescans
metadata                            exists

                                    Subtitle indexing
Subtitles           🟢 Implemented                          High         Medium   Integrate Jellyfin
                                    exists

                    🟡 Adapter /
Thumbnails                          Capability exists      Medium       High     Make cache-aware
                    contract

                    🔴 Documented
                                    Requires metadata
Posters/backdrops   but not                                Medium       Medium   Delegate to Jellyfin
                                    providers
                    implemented

                                    Discovery but not
Media library       🟡 Partial                              High         High     Jellyfin integration
                                    full UX
       Feature         Category           Current state            Value      Risk                Action

                    🔴 Documented
                                      No complete                            Very
Playback            but not                                  High                      Delegate
                                      playback product                       high
                    implemented

                                      Transfer endpoints                               Implement range
HTTP streaming      🟡 Partial                                High            High
                                      may support it                                   semantics

                    🟡 Adapter /       Depends on
Seeking                                                      High            High      Support cautiously
                    contract          range/cache

                    🔴 Documented
                                      FFmpeg provider                        Very
Transcoding         but not                                  High                      Delegate to Jellyfin
                                      only                                   high
                    implemented

Watch history       🔴 Missing         No full OTT state      Medium          Medium    Jellyfin owns

Continue watching   🔴 Missing         No full OTT state      Medium          Medium    Jellyfin owns

OTT                 ⚪ Future / idea   Product concept        Medium          Extreme   Do not build

                    🟢 Implemented     Local control center
Web UI                                                       High            Medium    Productize
                    + tested          exists

                                      Control-plane auth                               Strengthen
Authentication      🟡 Partial                                Critical        High
                                      exists                                           sessions/RBAC

                                                             Low for
Profiles            🔴 Missing         OTT feature                            Medium    Do not prioritize
                                                             TelDrive core

Playlists           🔴 Missing         Media-client feature   Low/Medium      Medium    Jellyfin

Recommendations     🟠 Experimental    Intelligence exists    Low             High      Keep advisory

TV support          🔴 Missing         No clients             Low for core    High      Jellyfin

Mobile client       🔴 Missing         No native product      Medium          High      PWA/API first

Desktop client      🔴 Missing         No native product      Low/Medium      High      Use rclone/WebDAV

Casting             ⚪ Future / idea   Not implemented        Low             High      Do not build

                                      Control-plane APIs
REST API            🟢 Implemented                            Critical        Medium    Stabilize/version
                                      exist

                    🔴 Documented                                                       Important next
                                      No complete
WebDAV              but not                                  High            High      interoperability
                                      protocol layer
                    implemented                                                        feature

S3                  ⚪ Future / idea   Not implemented        Medium          High      Gateway later

                    🟡 Adapter /
FUSE                                  rclone route exists    Medium          High      Do not own
                    contract

SMB                 ⚪ Future / idea   Not implemented        Low             High      Do not build

NFS                 ⚪ Future / idea   Not implemented        Low             High      Do not build

                    🟡 Adapter /
PDF extraction                        Optional tooling       Medium          Medium    Keep optional
                    contract
      Feature             Category           Current state            Value      Risk              Action

                       🟡 Adapter /                                                        Deterministic
OCR                                      Tesseract optional     Medium/High     Medium
                       contract                                                           pipeline

                       🟡 Adapter /
Transcription                            Whisper optional       Medium          High      Queue and cache
                       contract

                       🟡 Adapter /       Deterministic/local
Embeddings                                                      Medium          Medium    Opt-in
                       contract          options

Semantic search        🟢 Implemented     Ranking exists         Medium/High     Medium    Measure actual value

Visual similarity      ⚪ Future / idea   Not established        Low             High      Do not prioritize

Natural-language                                                                          Layer on
                       🟠 Experimental    Possible with AI       Medium          Medium
search                                                                                    deterministic search

Archive
                       🟢 Implemented     Intelligence exists    High            Medium    Keep non-destructive
recommendations

Storage                                                                                   Productize
                       🟢 Implemented     Analytics exists       High            Medium
optimization                                                                              dashboards

                                                                                          Improve confidence
Media classification   🟡 Partial         Providers exist        Medium          Medium
                                                                                          display

Anomaly detection      🟠 Experimental    Not core               Medium          High      Later

                                         Durable jobs support                             Add user-friendly
Scheduler              🟢 Implemented                            Critical        Medium
                                         scheduling                                       policies

                                         Workflow concepts
Event triggers         🟡 Partial                                High            High      Define event model
                                         exist

Workflow                                 Durable execution
                       🟢 Implemented                            High            Medium    Expose in UI
dependencies                             supports it

                                                                                          Add
                       🟢 Implemented     Alerts and
Notifications                                                   High            Low       Telegram/webhook
                       + tested          notifications exist
                                                                                          options

External               🟡 Adapter /       Some provider
                                                                High            Medium    Prioritize webhooks
integrations           contract          boundaries

                       🟡 Adapter /       Local workflow
AI planning                                                     Medium          High      Review-only
                       contract          planning exists

                       🟡 Adapter /       Safety boundary                        Very      Narrow allowlisted
AI execution                                                    Medium
                       contract          specified                              high      actions

                       🟢 Implemented     Health/job                                       Add SLO-like
Monitoring                                                      Critical        Low
                       + tested          monitoring exists                                indicators

                                         Trusted boundary
Remote workers         🟠 Experimental                           Low currently   High      Delay
                                         exists

                       🟢 Implemented
Control Center                           Local HTML UI exists   Critical        Medium    Turn into product
                       + tested

                                         Not appropriate at
Full multi-user SaaS   ⚪ Future / idea                          Low             Extreme   Reject
                                         ₹0
M. Ownership Boundaries
      Responsibility           TelDrive                  rclone             Jellyfin         External/optional

 Storage                                                              Consume
                       Own                        Adapter engine                         Other providers
 abstraction                                                          filesystem/API

 Byte transfer         Policy and jobs            Execute transfers   Playback reads     FFmpeg

                                                  Consume
 Telegram provider     Own adapter                                    Indirect           Telegram
                                                  TelDrive remote

                                                  File metadata       Own media
 Metadata/indexing     Own canonical index                                               OCR/Whisper
                                                  only                database

 Media library         Export/discovery           Mount only          Own                Metadata providers

 Playback              Basic previews/range API   Not responsible     Own                Browser/native clients

 Transcoding           Orchestrate only           Not responsible     Own                FFmpeg

 Authentication        API/control-plane auth     Config tokens       Media auth         Reverse proxy/SSO

                       Files/documents/global
 Search                                           Basic listing       Media search       Tantivy/SQLite
                       index

 AI                    Advisory orchestration     None                Optional plugins   Ollama/llama.cpp

                                                  Command
 Automation            Storage workflows                              Webhooks/plugins   systemd, n8n
                                                  execution

 Snapshots             Own                        Copy primitives     Not responsible    Local filesystems

                       Own policy and
 Backups                                          Transport           Not responsible    Restic/Borg later
                       verification

                       REST, HTTP, limited
 Protocol access                                  Mount/remotes       Media API          Gateway projects
                       WebDAV

 Notifications         Own events                 Logs                Plugins/webhooks   Telegram/email/webhooks

                       Durable jobs and worker                        Transcoding
 Workers                                          Transfer process                       Remote workers later
                       contracts                                      process


N. Automation Strategy
TelDrive should own
      scheduled backups;
      snapshot creation;
      retention;
      archive workflows;
      integrity verification;
      duplicate reports;
      provider evacuation;
    ingestion pipelines;
    transfer dependencies;
    retries;
    notifications;
    pause/resume;
    approval gates;
    job history.

Delegate to existing tools
    system scheduling: systemd timers and cron;
    general workflow composition: n8n, Node-RED, or shell;
    home automation: Home Assistant;
    CI-driven workflows: GitHub Actions where appropriate;
    media metadata and playback automation: Jellyfin ecosystem;
    generic file transfer: rclone.
TelDrive should expose:
    CLI;
    REST API;
    webhooks;
    event stream;
    idempotent job triggers;
    dry-run mode;
    job status endpoints.
Do not build a full general-purpose automation platform.

O. Top Product Priorities
  Rank              Priority            Value       Difficulty   ₹0 feasibility   Leverage     Risk
           Provider capability                                                        Very
     1                               Very high       Medium              High                Medium
           abstraction                                                                high

           Universal manifests and                                                    Very
     2                               Very high       Medium              High                  Low
           export                                                                     high

           Telegram rate-aware                                                        Very
     3                               Very high          High             High                  High
           transfer scheduler                                                         high

           Local cache and                                                            Very
     4                               Very high   Medium/High             High                Medium
           materialization modes                                                      high
  Rank              Priority                  Value       Difficulty       ₹0 feasibility   Leverage      Risk

         Disaster recovery and                                                                  Very
     5                                    Very high           High                 High                   High
         provider evacuation                                                                    high

     6   Productized control center       Very high        Medium                  High        High    Medium

         Stable versioned REST API                                                              Very
     7                                    Very high        Medium                  High                Medium
         and CLI                                                                                high

         WebDAV read/write
     8                                         High    Medium/High                 High        High       High
         adapter

         Jellyfin integration guide
     9                                         High        Medium                  High        High    Medium
         and tooling

         Media-aware cache and
    10                                         High        Medium                  High        High    Medium
         prefetch

         Search/indexing
    11                                         High        Medium                  High        High    Medium
         consolidation

         Ingestion pipeline with
    12                                         High        Medium                  High        High    Medium
         verification

         Provider health and
    13                                         High        Medium                  High        High       Low
         capability dashboard

         Snapshot/restore drill
    14                                         High        Medium                  High        High    Medium
         tooling

         Webhooks and external
    15                                Medium/High          Medium                  High        High       Low
         automation integration

         Local OCR/transcription as
    16                                     Medium          Medium                  High     Medium     Medium
         optional jobs

    17   AI natural-language search        Medium      Medium/High              Medium      Medium     Medium

                                                                          High software,
    18   S3 gateway                        Medium             High            moderate      Medium        High
                                                                              hardware

    19   Remote workers               Low currently           High     Low operationally        Low       High

                                      Low strategic
    20   Full OTT                                          Extreme                  Low     Negative   Extreme
                                                 fit


Zero-cost interpretation
Most software can be open source and run at ₹0 infrastructure cost on a personal Linux
machine. That does not make the operation costless:
    Telegram bandwidth still consumes network capacity.
    Local disks, electricity, and backup media have real costs.
    Transcoding consumes CPU/GPU resources.
    Mobile or remote access may require a public IP, VPN, domain, or relay.
    Large external replicas may eventually require paid storage.
    AI models can consume substantial RAM, CPU, and disk.
A credible ₹0 deployment should target:
    one modest Linux machine;
    SQLite/PostgreSQL only where necessary;
    local indexing;
    optional containers;
    rclone;
    Jellyfin;
    Tesseract;
    FFmpeg;
    small local models only;
    no Kubernetes;
    no mandatory cloud service;
    no managed search cluster.

P. DO NOT BUILD
TelDrive should explicitly refuse to build or defer:
  1. A complete OTT platform.
  2. A Netflix-like recommendation system.
  3. Native TV clients before a stable backend proves demand.
  4. A replacement for rclone.
  5. A custom filesystem with POSIX guarantees.
  6. SMB and NFS servers for remote Telegram storage.
  7. A second media server competing with Jellyfin.
  8. A general-purpose workflow automation platform.
  9. Autonomous AI deletion or retention.
10. A multi-tenant public Telegram storage service.
11. Account-farm or anti-enforcement mechanisms.
12. A massive search cluster for personal installations.
13. Mandatory embeddings for every object.
14. CAS/deduplication mutation before robust reporting is proven.
15. Distributed workers before local job semantics are mature.
16. A hard dependency on Telegram.
17. A promise of unlimited storage or throughput.
18. A paid-API-dependent core.
19. Full enterprise collaboration and document editing.
20. Complex microservice decomposition for a single-user machine.

Q. Recommended Architecture
                              Control Center / CLI / REST
                                             │
                              Policy + Authorization Layer
                                             │
                              Durable Job and Workflow Engine
                                            │
                ┌───────────────────┬──────┴────────┬───────────────────┐
                │                   │               │                   │
     Transfer Scheduler      Archive Manager       Search/Indexing   Automation Events
                │                   │               │                   │
                └───────────────────┴──────┬────────┴───────────────────┘
                                            │
                                 Provider Capability API
                                         │
          ┌───────────────┬──────────────┼───────────────┬───────────────┐
          │               │              │               │               │
      Telegram           Local FS         rclone           WebDAV           S3
          │               │              │               │               │
          └───────────────┴──────────────┴───────────────┴───────────────┘
                                         │
                               Manifests + Checksums + Audit
                                             │
                              Cache / Materialization Layer
                                             │
                         Jellyfin / WebDAV / HTTP / Scripts


Canonical data model
TelDrive’s database should be authoritative for:
    logical objects;
    paths;
    object versions;
    hashes;
    chunks;
    provider references;
    replicas;
    verification evidence;
    lifecycle state;
    job state;
    audit events;
    search metadata.
Telegram message IDs should be treated as provider references, not canonical identity.

Storage modes
TelDrive should expose explicit modes:
    Hot local: materialized locally for frequent access.
    Warm remote: remote source with cache.
    Cold archive: low-frequency, integrity-verified storage.
    Immutable snapshot: deletion-protected according to policy.
    Migration mode: copying away from a provider.
    Degraded mode: provider unavailable, cached data remains usable.

Security model
    Separate read and mutation permissions.
    Require explicit authorization for destructive plans.
    Use allowlisted paths and providers.
    Keep Telegram session credentials outside the database where possible.
    Encrypt sensitive local metadata and secrets.
    Make audit logs append-oriented.
    Require verification before deleting source data.
    Never let AI or UI directly mutate the provider.

R. Product Evolution
Stage 1 — Foundation
Already substantially achieved:
    project structure;
    configuration;
    metadata;
    safety boundaries;
    durable jobs;
    transfer workflows;
    verification;
    audit;
    backups;
    search foundations;
    monitoring;
    control center;
    optional local intelligence.
The main remaining work is not another foundation phase. It is consolidation and proof.

Stage 2 — Productization
Build the first coherent product:
    installation and upgrade path;
    simple setup wizard;
    provider capability display;
    job templates;
    storage health dashboard;
    archive workflow UI;
    clear degraded-state handling;
    CLI parity;
    stable API;
    real documentation based on tested behavior.
Success criterion: a new user can install TelDrive, connect one provider, upload, verify, search,
snapshot, restore, and understand failure states.

Stage 3 — Provider independence
Add:
    local filesystem provider;
    WebDAV provider;
    robust rclone provider;
    provider migration;
    manifest export/import;
    capability negotiation;
    provider evacuation;
    test suites for provider behavior.
Success criterion: removing Telegram does not destroy the product.
Stage 4 — Interoperability
Add:
    HTTP range access;
    limited WebDAV;
    Docker volume integration;
    Jellyfin setup tooling;
    cache/materialization controls;
    webhooks;
    external automation hooks.
Success criterion: external applications can consume TelDrive without bypassing its safety
model.

Stage 5 — Media integration
Do not build an OTT. Instead:
    export media libraries to Jellyfin;
    support metadata and thumbnail caching;
    provide prefetch;
    monitor remote media latency;
    support direct-play-oriented setups;
    make local materialization easy.
Success criterion: personal media works acceptably for a small household without pretending
Telegram is a NAS.

Stage 6 — Automation
Add:
    scheduled ingestion;
    archive policies;
    snapshot schedules;
    verification schedules;
    notifications;
    approval workflows;
    event triggers;
    job dependency visualization.
Success criterion: common repetitive storage operations become reliable and observable.
Stage 7 — Intelligence
Add only after deterministic foundations are measured:
    natural-language search;
    archive recommendations;
    duplicate explanations;
    document/media classification;
    summaries;
    AI-generated workflow drafts.
Success criterion: intelligence saves time without creating unsafe mutations.

Stage 8 — Advanced experiments
Only later consider:
    trusted remote workers;
    distributed transcoding;
    content-addressed storage;
    advanced visual similarity;
    S3 gateway;
    third-party plugin ecosystem.
These should remain optional and must not complicate the core installation.

S. Biggest Risks
Telegram dependency
The primary risk is not simply an API outage. It is that Telegram changes the economics or
operational assumptions of the project:
    stricter rate limits;
    changed file limits;
    account restrictions;
    channel deletion;
    API changes;
    access failures;
    changed retention behavior.
Mitigation: provider abstraction, manifests, replicas, cache, migration, and explicit degraded
mode.
Rate limiting and throughput
Telegram may be perfectly usable for asynchronous archive jobs but unsuitable for random-
access workloads. The application must treat flood waits as normal control signals, not
exceptional bugs.

Account restrictions
A personal user account or channel can become unavailable. A single-account system is
therefore not an acceptable sole backup architecture.

Scope explosion
The existing feature list spans storage, backup, search, media, AI, workflows, distributed
workers, and UI. Without ruthless prioritization, TelDrive will become a collection of adapters
rather than a dependable product.

OTT complexity
Playback is not “serve a video file.” A credible OTT requires clients, profiles, playback state,
metadata, transcoding, device compatibility, security, and maintenance. Jellyfin already exists
for this purpose.

Ecosystem dependency
rclone and Jellyfin are enormous leverage, but version changes and integration behavior must
be tested. TelDrive should maintain compatibility tests instead of copying their functionality.

Zero-cost constraints
₹0 infrastructure is realistic for a personal, local deployment. It is not realistic as a promise of
highly available remote access, redundant storage, heavy transcoding, and large-scale multi-
user service.

T. Final Verdict
If responsible for TelDrive, I would build next:
  1. Provider abstraction and capability negotiation.
  2. Universal manifests and provider-independent object identity.
  3. Telegram-aware scheduling, backpressure, flood-wait handling, and caching.
  4. Export, restore, and provider-evacuation workflows.
  5. A polished control center and stable CLI/API.
  6. Limited WebDAV and strong HTTP range access.
  7. Jellyfin integration with media caching and materialization.
  8. Deterministic search consolidation.
  9. Ingestion pipelines with verification.
10. Safe scheduling, webhooks, notifications, and approval workflows.
I would explicitly refuse to build:
    a custom OTT;
    a replacement for Jellyfin;
    a replacement for rclone;
    a custom POSIX filesystem;
    a public multi-user Telegram storage service;
    autonomous destructive AI;
    an assumption that Telegram storage is unlimited;
    unnecessary SMB/NFS support;
    complex distributed workers before the single-machine product is excellent.
The strongest TelDrive is not “Google Drive but free through Telegram.” That positioning
creates promises the system cannot safely keep.
The strongest TelDrive is:
         A local-first, auditable storage operating layer that turns unreliable and heterogeneous
         backends—including Telegram—into manageable personal archives, backup
         workflows, and media integrations.
That identity is technically defensible, feasible with open-source software at ₹0 infrastructure
cost for personal use, differentiated from ordinary file browsers, and resilient if Telegram
eventually becomes less attractive.
                                                            ⁂


  1. https://github.com/tgdrive/teldrive/issues
  2. https://github.com/tgdrive/teldrive/issues/86
  3. https://github.com/tgdrive/teldrive/issues/483
  4. https://github.com/tgdrive/teldrive/issues/255
  5. https://rclone.org/commands/
  6. https://deepwiki.com/tgdrive/teldrive-docs/4.2-media-server-integration
  7. https://jellyfin.org/docs/general/administration/storage/
  8. https://jellyfin.org/docs/general/clients/
  9. https://jellyfin.org/docs/general/clients/codec-support/
 10. https://github.com/EdisonJwa/tg-rclone
 11. https://telegram.org/faq
 12. https://telegram.org/privacy?setln=be
 13. https://core.telegram.org/bots/api
 14. https://core.telegram.org/api/files
15. https://core.telegram.org/api/config
16. https://telegram.org/tos
17. https://github.com/tgdrive/teldrive/issues/97
18. https://github.com/tgdrive/teldrive/issues/460
19. https://jellyfin.org/docs/
20. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/
21. https://jellyfin.org/docs/general/post-install/transcoding/
22. https://docs.nextcloud.com/server/stable/user_manual/en/files/access_webdav.html
23. https://github.com/GiacomoFicarola/TelegramDrive
24. https://github.com/tgdrive/teldrive
25. https://github.com/birdup000/RcloneTelegram
26. https://github.com/tgdrive/teldrive/blob/main/README.md
27. https://github.com/saidjons/teldrive-go
28. https://github.com/PrivacyProjectTeam/teldrive-2024
29. https://github.com/rclone/rclone/issues/5829
30. https://github.com/Sayrix/tgdrive-rclone/blob/main/docs/content/teldrive.md
31. https://telegramhpc.com/news/1013/
32. https://teldrive-docs.pages.dev/docs/guides/rclone
33. https://www.scribd.com/document/736327452/docs-telethon-dev-en-stable
34. https://deepwiki.com/tgdrive/teldrive-docs/4-integration
35. https://jellyfin.org/docs/general/administration/hardware-selection/
36. https://github.com/jellyfin-archive/jellyfin-docs/blob/master/general/administration/hardware-acceleration.md
37. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/nvidia/
38. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/intel/
39. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/amd/
40. https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/rockchip/
41. https://wiki.nixos.org/wiki/Jellyfin
42. https://jellyfin-jellyfin.mintlify.app/setup/hardware-acceleration
43. https://docs.nextcloud.com/server/30/go.php?to=user-webdav
44. https://docs.nextcloud.com/server/stable/developer_manual/client_apis/WebDAV/index.html
45. https://docs.nextcloud.com/server/19/user_manual/files/access_webdav.html
46. https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html
47. https://nextcloud.com/files/
48. https://docs.nextcloud.com/server/27/user_manual/en/files/access_webdav.html
49. https://rclone.org/commands/rclone_bisync/
50. https://indico.cern.ch/event/336753/contributions/1726347/attachments/658854/905703/Seafile__Cloud_Storage_Pla
    tform.pdf
51. https://indico.cern.ch/event/565381/contributions/2402042/attachments/1403453/2143299/Drive_Client_and_Realtim
    e_Backup.pdf
52. https://www.vpsbg.eu/blog/open-source-software-review-nextcloud
53. https://deepwiki.com/nextcloud/documentation/4.1-file-management-and-access
54. https://www.seafile.com/en/features/
55. https://homeserver.page/app/seafile
56. https://core.telegram.org/api/bots/ai
57. https://core.telegram.org/api/errors
58. https://telegram.org/tos/bot-developers
59. https://docs.telethon.dev/en/stable/quick-references/faq.html
60. https://grammy.dev/advanced/flood
61. https://www.itechguides.com/how-to-use-telegram-as-cloud-storage-for-files-and-photos/
62. https://www.quarkip.com/blog/guides/4184
63. https://telegramvault.org/blog/telegram-flood-restriction-vs-shadowban-vs-ban-2026
64. https://www.scribd.com/document/524623882/telethon1
65. https://www.aeanet.org/how-to-access-telegram-cloud/
66. https://prmotion.me/en/post/how-to-bypass-floodwait-limits-in-telegram-and-configure-stable-automation
67. https://youreputationsolution.com/services/recovery-telegram-account/
68. https://github.com/pong106/telegram-rclone
69. https://github.com/tgdrive/teldrive/issues/473
70. https://github.com/tgdrive/teldrive/issues/88
71. https://github.com/tgdrive/teldrive/issues/108
72. http://github.com/topics/rclone
73. https://en.wikipedia.org/wiki/Jellyfin
74. https://nextcloud.com/faq/
75. https://github.com/jellyfin/jellyfin/blob/master/LICENSE
76. https://github.com/jellyfin/jellyfin
77. https://github.com/jellyfin/jellyfin-web
78. https://github.com/jellyfin/jellyfin-android/blob/master/LICENSE.md
79. https://github.com/orgs/jellyfin/repositories
80. https://github.com/jellyfin/jellyfin-desktop
81. https://github.com/jellyfin/jellyfin/issues/8226
82. https://gitlab.com/jellyfin/jellyfin/-/blob/master/LICENSE
83. https://github.com/nextcloud/server/blob/master/COPYING-README
84. https://github.com/jellyfin/jellyfin-android
85. https://github.com/jellyfin/jellyfin-plugin-template/blob/master/LICENSE
86. https://github.com/jellyfin
87. https://github.com/rolehippie/rclone/blob/master/LICENSE
