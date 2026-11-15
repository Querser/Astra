# AI usage and asset provenance

## Local model

ASTRA uses **Qwen3-8B**, identified by the Ollama tag `qwen3:8b`, as its local
language model. Ollama serves the model on the user's computer. The repository
does not contain Ollama or the model weights; the setup process installs or
downloads them separately when required.

The model drafts assistant responses from a bounded selection of conversation
context, profile measurements, forecasts, and local knowledge documents.
Application code performs structured storage, retrieval, validation, and
statistical forecast calculations. The model does not replace those calculations.

## Visual design and generated assets

Generative AI assisted the visual design of the ASTRA interface and presentation.
It also created the following project-owned image:

- `frontend/src/assets/astra-anatomy-atlas.png` - an AI-generated anatomical
  illustration based on a user-supplied reference for composition and proportions.

The application displays an `AI-GENERATED IMAGE` watermark over the anatomical
illustration and repeats the disclosure below the image. The original reference
image is not distributed in this repository.

`docs/astra-chat-forecast-2026-11-08.png` is a screenshot captured from the ASTRA
interface. It reflects the AI-assisted interface design, but the screenshot itself
was not generated as a new synthetic image.

## Human responsibility

The project authors selected the product requirements, reviewed the implementation,
assembled the local knowledge materials, and remain responsible for the submitted
project. AI assistance does not establish medical validity or transfer responsibility
for the software's behavior.

Related licensing and source information appears in
[Third-party notices](../THIRD_PARTY_NOTICES.md).
