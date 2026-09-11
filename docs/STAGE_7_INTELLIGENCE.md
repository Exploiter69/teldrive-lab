# Stage 7 — Intelligence

## Goal

Add useful intelligence without turning TelDrive Lab into an autonomous storage administrator or requiring a large language model on the primary laptop.

## Product contract

```text
Deterministic retrieval
        ↓
Optional interpretation / advisory AI
        ↓
Policy
        ↓
Authorization
        ↓
Execution
        ↓
Verification
        ↓
Audit
```

The intelligence layer may search, explain, classify, summarize, and recommend. It does not receive storage authority.

## Implemented capabilities

- lexical and metadata search with deterministic scoring
- structured extension, size, and name filters
- deterministic natural-language query parsing over the existing index
- OCR indexing through Tesseract when locally installed
- transcript indexing through the local Whisper CLI when installed
- duplicate explanations from existing SHA-256 evidence
- anomaly explanations for integrity risk and unusually large objects
- explainable organization suggestions
- metadata enrichment suggestions
- zero-LLM extractive document/transcript summaries
- rebuildable intelligence export with a digest
- optional local Ollama adapter, explicitly selected by the caller
- capability reporting for optional tools

## Resource boundary

The Stage 7 host gate does **not** load a model, contact a remote AI provider, require a GPU, or require Ollama/llama.cpp/Tesseract/Whisper to be installed.

The core intelligence path is deterministic and suitable for the primary i5-1235U / 8 GB RAM environment. Optional AI is a sidecar, not a dependency.

The optional Ollama adapter has no default model selection. A caller must explicitly select a model. This prevents accidental startup of a large model merely because Stage 7 is enabled.

## AI authority boundary

Every AI/intelligence proposal is non-authoritative and requires policy and authorization. In particular, intelligence cannot independently:

- delete data
- overwrite data
- change retention
- authorize cleanup
- restore over existing content
- expose private data
- migrate the only verified copy

Duplicate intelligence is report-only. A duplicate explanation never implies deletion.

## OCR / transcript boundary

OCR and speech-to-text are capability-gated local tools. Their absence is reported rather than treated as a failure of the core product.

Transcripts and OCR text are derived data and remain rebuildable. The intelligence layer does not mutate production TelDrive storage.

## What Stage 7 does not build

- a mandatory LLM runtime
- a large local model deployment
- a paid AI API dependency
- autonomous storage administration
- a vector database requirement
- Elasticsearch/OpenSearch infrastructure
- an AI-controlled transfer worker
- a new media server

## Exit criteria

Stage 7 is complete when the full regression suite and `scripts/stage7_intelligence_gate.py` pass, with production storage mutation reported as `NONE`.
