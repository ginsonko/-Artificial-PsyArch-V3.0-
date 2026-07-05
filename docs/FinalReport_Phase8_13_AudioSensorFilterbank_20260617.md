# Phase 8.13 Final Report - Audio Sensor Filterbank

## Design

Phase 8.13 adds an audio sensor adapter:

- active filterbank bands become audio percept SA
- rhythm buckets become audio rhythm SA
- audio events enter `StatePool` like text and vision events

## Review

The adapter does not perform speech recognition. It only exposes normalized audio SA for later AP-native learning.

## Landing

Added:

- `runtime/sensor_adapters/audio/filterbank.py`
- `tests/test_phase8_13_audio_sensor.py`

Updated:

- `config/apv3_constants.yaml`

## Validation

Targeted tests verify:

- band/rhythm events are emitted
- audio events can spawn PERCEIVED markers in the state pool

## Boundary

This phase proves the audio adapter template, not natural speech understanding.
