# Phase 8.12 Final Report - Fast Mapping + Reverse Imagination

## Design

Phase 8.12 implements minimal fast mapping:

- unknown label SA competes over visual candidate SA
- shape channel has a governed structural bias
- low support injects epistemic drive as unfinished pressure
- learned mapping can produce a reverse-imagined visual SA

## Review

The implementation does not parse Chinese words. It only uses normalized channel signatures from the sensor adapter.

## Landing

Added:

- `runtime/cognitive/fast_mapping/mapper.py`
- `tests/test_phase8_12_fast_mapping.py`

Updated:

- `config/apv3_constants.yaml`

## Validation

Targeted tests verify:

- shape candidate wins over same-energy color candidate
- mapping gap raises cognitive pressure through ledger
- reverse imagination can spawn IMAGINED marker

## Boundary

This phase proves the fast-mapping substrate, not arbitrary word learning or raw visual recognition.
