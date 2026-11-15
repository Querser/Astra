# Internal Research Knowledge Base of ASTRA

**Status:** `research_only`, 2026-11-07. These materials remain as project notes and are not loaded into the model. A small separate [executable catalog of diagnostic demo versions](../../../backend/reference_docs/ASTRA_DEMO_DIAGNOSTIC_CANDIDATES.json) is separately connected, using verified original sources. ASTRA is not a clinically validated medical device.

## Boundary of this package

Only measurements without taking biological samples, crew messages and operational context for which one can describe the method of acquisition and the degree of confirmation of availability. **Blood, urine, laboratory panels and any research on samples are excluded from the current scope**, including active definitions, rules, examples and interface. Possible later work with them does not add them to the current database.

The package consists of [availability matrix](availability.md), [templates and relations](templates-and-relations.md), [reference notes](reference-and-domain-notes.md), [source ledger](source-ledger.md), and [safety boundaries and stages](safety-and-roadmap.md). Notes describe what is confirmed by the source, what is only assumed, and what remains unknown. Full texts of third-party medical documents are not copied here.

## Source of Truth and Link to the Project

This package is a **research draft in Markdown**. Conditional comparisons are in [`reference_checks.py`](../../../backend/app/reference_checks.py), and four named sample versions are in a separate JSON directory. General rules are stored separately from personal SQLite records. To expand the directory, source verification, input availability, methodology, and tests are needed. The previous [ADR-002](../ADR-002-knowledge-architecture.md) is preserved as a historical project, not as current instructions.

The term 'card' in the interface currently refers to a CSS panel, not a medical data type. Here, precise types are used: definition of measurement `M.*`, definition of context `C.*`, reference indication `R.*`, rule description `A.*`, source `E.*`, and type of relation `L.*`. Personal profile, examination, and original series are instances of SQLite, not general documents. Existing `DataSource` indicates, **who or what created a specific record**; `E.*` indicates, **which publication supports a general assertion**.

## How to Read Availability Classes

Classes 1–5 in the matrix mean: (1) direct sensor/system on board or in the suit is confirmed; (2) non-invasive device or procedure is possible, but continuous availability of ASTRA is not confirmed; (3) message from a person or manual input; (4) calculation from observations/schedule; (5) experimentally or insufficiently confirmed. **Class 1 does not mean that ASTRA receives a stream**: for that, a separately verified interface, access resolution, and usage conditions are needed. Class 3 does not become a sensor indication just because it is entered into an electronic form.

Each subsequent knowledge entry goes through the same filter: specific purpose, method of input acquisition, source and population, rights, conditions and units, useful distinction from existing entry, versioning and responsible for review. Duplicates, broad "lists of all diseases", statements without source, or rules for which it is impossible to obtain necessary inputs are not added. Absence of information is always shown as unknown, not as a normal value.
