# Phase 17 Design - Real Visual Asset Seed

Date: 2026-06-18

## Design

Phase 17 adds the first external real-photo visual asset seed. Phase 14 intentionally used local synthetic assets to prove governance without copyright risk. Phase 17 keeps that proof intact and creates a separate `real_manifest.yaml` for vetted Wikimedia Commons photos.

The first seed is deliberately small and strict:

- 3 fruit concepts: apple, banana, orange
- 15 PNG images: 3 train + 1 held-out + 1 contrast per concept
- accepted license families only: Public Domain Mark, CC0, and CC-BY
- no CC-BY-SA in the first seed
- source URLs and attribution recorded for every file

## Review

Adversarial review found that broad Commons search can return paintings, card illustrations, people-context images, or invalid thumbnail responses. The downloader therefore:

- filters known non-photo title contexts;
- skips CC-BY-SA and unsupported licenses;
- downloads through Commons metadata, not arbitrary web scraping;
- converts downloaded images into compact PNGs;
- writes a source sidecar for audit;
- keeps Phase 14's synthetic manifest unchanged.

## Landing Plan

- `scripts/curriculum/download_real_visual_assets.py`
- `config/curriculum/assets/real_manifest.yaml`
- `config/curriculum/assets/visual/real/*.png`
- `config/curriculum/assets/visual/real/_sources.json`
- `config/curriculum/packages/real/real_fruit_photos_v1.yaml`
- targeted Phase 17 tests
- public-readable showcase page

## Boundary

Phase 17 proves the asset-governance path for a first real-photo seed. It does not claim a large open dataset, complete object vocabulary, automatic semantic understanding from pixels, or public release legal completion.
