# Third-party materials and sources

ASTRA's `LICENSE` applies only to rights held by the ASTRA project author. The
components and research sources below retain their own terms. Links identify
their original publishers; citing a source does not mean that the publisher
endorses ASTRA.

## Local model and runtime

| Component | Role | Upstream terms |
| --- | --- | --- |
| [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | Optional, separately downloaded local model (`qwen3:8b`) | Apache-2.0; see the [model's license](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE). Model weights are not included in this repository. |
| [Ollama](https://github.com/ollama/ollama) | Separately installed local model server | MIT; see its [license](https://github.com/ollama/ollama/blob/main/LICENSE). The executable is not included in this repository. |

## Direct software dependencies

Packages are installed from the Python and npm registries. Their code is not
relicensed by ASTRA. The version pins and complete dependency trees are in
`backend/requirements.lock` and `frontend/package-lock.json`; check the package
distribution for the exact notice when redistributing a bundled build.

| Package | License | Package or source |
| --- | --- | --- |
| FastAPI | MIT | [fastapi](https://github.com/fastapi/fastapi) |
| SQLAlchemy | MIT | [sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| Alembic | MIT | [alembic](https://github.com/sqlalchemy/alembic) |
| Uvicorn | BSD-3-Clause | [uvicorn](https://github.com/Kludex/uvicorn) |
| HTTPX (test) | BSD-3-Clause | [httpx](https://github.com/encode/httpx) |
| pytest (test) | MIT | [pytest](https://github.com/pytest-dev/pytest) |
| React and React DOM | MIT | [react](https://github.com/facebook/react) |
| Vite and the React plugin | MIT | [vite](https://github.com/vitejs/vite), [plugin-react](https://github.com/vitejs/vite-plugin-react) |
| Tailwind CSS, PostCSS and Autoprefixer | MIT | [tailwindcss](https://github.com/tailwindlabs/tailwindcss), [postcss](https://github.com/postcss/postcss), [autoprefixer](https://github.com/postcss/autoprefixer) |
| TypeScript | Apache-2.0 | [typescript](https://github.com/microsoft/TypeScript) |
| React type definitions | MIT | [types/react](https://www.npmjs.com/package/@types/react), [types/react-dom](https://www.npmjs.com/package/@types/react-dom) |
| Playwright (test) | Apache-2.0 | [playwright](https://github.com/microsoft/playwright) |

## Packaged research data

The following local archival CSVs are in `backend/data/research/`. They are
external research data, not measurements of ASTRA's fictional crew and not
ASTRA-authored material. Their file names, source URLs, versions, retrieval date,
and SHA-256 checksums are recorded in
[the manifest](backend/data/research/manifest.json).

| Dataset | Source and acknowledgement |
| --- | --- |
| RadLab DosTel1 ISS radiation series | [RadLab Data API](https://visualization.osdr.nasa.gov/radlab/gui/data-api/), portal version 1.1.2. Data and visualizations courtesy of the RadLab Portal. See the [OSDR citation guidance](https://science.nasa.gov/reference/osdr-faq/). |
| OSD-575 transformed comprehensive metabolic panel | [NASA OSDR study OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575), version 3; use the study page's dataset citation when reusing the data. See the [OSDR terms](https://science.nasa.gov/reference/osdr-help-terms-and-conditions/). |

The linked local knowledge cards summarize outside scientific and medical
publications. They do not include the full publications or grant a license to
republish them. Individual sources, sections and limits are listed in
[the source registry](docs/knowledge/internal/source-ledger.md) and
[space-science source list](docs/space-science-sources.md).

## Visual assets and private records

`frontend/src/assets/astra-anatomy-atlas.png` is an AI-generated illustration,
marked as such in the interface. A user-supplied anatomical image was used as a
visual reference; the original image is not distributed. The project license
covers the illustration only to the extent that the project author holds rights
to grant. Confirm rights in the source reference before redistributing the
illustration outside the submitted project.

`docs/astra-chat-forecast-2026-11-08.png` is a screenshot of the ASTRA interface.
Local SQLite databases, logs and user-entered records are not part of the
published project license and must not be uploaded with the source repository.
