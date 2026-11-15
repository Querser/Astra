# Stages 8–13 delivery notes

## Stage 8: psychological and environmental context

`/psychological-assessments` stores optional self-reported mood, stress and fatigue on a 0–10 scale under the explicit instrument name `self_report_unvalidated`. It does not infer crisis, diagnosis or suitability. `/environmental-measurements` stores provenance-tagged CO₂, temperature, humidity, radiation, noise, space-weather, gravity or workload context. No endpoint claims a health causal relation from these measurements.

## Stage 9: transparent what-if records

`/what-if-scenarios` persists user-supplied assumptions and returns explicit `causal_validity: not_established` and `clinical_validity: not_established`. This is an auditable comparison notebook, not a physiological simulator.

## Stage 10: crew and human handoff

`/crew-summary` contains only counts for fictional demo profiles. `/mission-readiness/{crew_id}` always returns `not_assessed`; it cannot clear a person for duty. `/emergency-handoffs` creates an operator-declared handoff, and acknowledgement is separately recorded. No measurement automatically creates an emergency workflow.

## Stage 11: local sync simulator

`/sync/events` stores only event type, idempotency key and SHA-256 payload fingerprint. Repeated idempotency keys return the existing event. `/sync/simulator/deliver` increments attempts and records an acknowledgement locally. It makes no network connection and is intentionally a simulator for future ground-center integration.

## Stage 12: UX and accessibility

The local UI uses native labelled forms, keyboard-operable controls, live status regions, explicit synthetic labels, non-color-only notices and an HTML-table alternative to the SVG history plot. It surfaces the assistant's unavailable or insufficient-evidence state and does not present a health score.

## Stage 13: test, documentation and repeatable demo

Run the backend and frontend according to their READMEs. In the UI, create a fictional profile and manual source, then select **Normal**, **Gradual**, **Missing**, and **Explicit escalation** with seed 42. Run deterministic analysis, ask the local assistant, and request a forecast. The forecast will initially refuse because the generated scenarios do not create the required seven-day history; this refusal is expected evidence of the data-sufficiency gate.

For a non-network verification, run `python -m pytest` in `backend` and `npm run build` in `frontend`. The demonstration is local-only, synthetic by default and not medically validated.
