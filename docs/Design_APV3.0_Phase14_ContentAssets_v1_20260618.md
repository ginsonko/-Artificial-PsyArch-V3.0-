# Phase 14 Design - Synthetic First Content Assets

Date: 2026-06-18

## Design

Phase 14 moves from Phase 13 curriculum substrate proof to a clean first content asset release. The first batch deliberately uses generated-local synthetic visual/audio assets so license, provenance, hash, held-out, and safety gates can be proven without external copyright or PII risk.

## Review

Accepted refinements:

- Use synthetic assets first; move external web assets to a later license-audit phase.
- Every asset carries `sha256`, `source_url`, `license_id`, `asset_origin`, `intended_use`, `held_out_group`, and `content_safety_review`.
- Train, held-out, and contrast material are separated at manifest and package level.
- Neutral foundation vocabulary is Codex-authored; style/persona corpora remain reserved for user + Claude writing.

## Landing Scope

- 14.0: content asset manifest governance.
- 14.1: generated-local PNG/WAV synthetic assets.
- 14.2: first neutral curriculum packs.
- 14.3: public-readable showcase and total report.

## Boundary

This phase does not claim 3500-character literacy, 7000-word vocabulary, real external image/audio corpora, full elementary math, style-persona text completion, web polish, legal release, or public alpha user study.
