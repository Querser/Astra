# Local Scientific ASTRA Cards

The catalog `backend/reference_docs/ASTRA_SPACE_SCIENCE.json` contains short author's summaries of primary materials. Date of verification and extraction: November 14, 2026. The fields `published_at` and `version` are equal to `null`, if these details could not be confirmed on the source page. Cards relate to general scientific information or engineering requirements; they are not personal measurements, OSD-575 research records, or archival points of RadLab.

## Sources and Application

| Source | Verified Content | Cards and Application Boundaries |
| --- | --- | --- |
| [NASA HRP — Five Hazards](https://www.nasa.gov/hrp/hazards/) | Radiation, isolation, remoteness, gravity, enclosed environment | `HRP.HAZARD.*`; mission condition binding to inputs, without diagnosis from general risk factor. |
| [NASA HRP — Risks](https://www.nasa.gov/hrp/risks/) | Cardiovascular adaptation, bone and muscle changes, SANS | `HRP.RISK.CARDIO`, `HRP.RISK.BONE`; pulse and pressure are interpreted with posture, activity, mission phase; bone changes cannot be derived from steps. |
| [NASA HRP — Ongoing Research](https://www.nasa.gov/hrp/ongoing-hrp-research/) | ARCHeR links sleep, activity, light and well-being; vision research includes OCT | `HRP.SLEEP.ARCHeR`, `HRP.RISK.VISION`; screen test detects change relative to own series, but does not confirm SANS. |
| [NASA HRR — Sleep Evidence Report](https://humanresearchroadmap.nasa.gov/evidence/reports/Sleep.pdf), release 11.04.2016 | Appendix A differentiates actigraphy, diary, and subjective scales | `HRR.SLEEP.METHODS`; method and its limitations must be preserved. |
| [CSA — Monitoring radiation](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp), 26.02.2026 | Development of an autonomous neutron instrument CANS | `CSA.RADIATION.CANS`; the article does not publish CANS data stream. |
| [CSA — Why conduct science in space](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp), updated 28.10.2025 | Communication delay and limited access to assistance on deep missions | `CSA.AUTONOMY.DEEP_SPACE`; explanation of local architecture. |
| [NASA-STD-3001 Vol 2](https://standards.nasa.gov/node/237), [PDF Rev F](https://standards.nasa.gov/system/files/tmp/NASA-STD-3001%20Vol%202%20Rev%20F.pdf) | Rev F is active on 14.11.2026 from 14.07.2026. §6.1 `[V2 6001]` requires data suitable for trend analysis; §6.2.1.3 `[V2 6004]` specifies average hourly ppCO₂ in the inhabited volume not exceeding 3 mmHg | `STD3001.V2.6001`, `STD3001.V2.6004`; the latter cannot be applied to instantaneous ppm or personal diagnosis. Conversion to ppm requires total pressure. |
| [NASA HIDH](https://www.nasa.gov/human-integration-design-handbook/) | Revision 1 serves as an engineering rationale reference to the standard | `HIDH.DESIGN.RATIONALE`; overview page does not set an independent numerical threshold. |

Links to Human Research Roadmap to individual reports [SANS](https://humanresearchroadmap.nasa.gov/evidence/reports/SANS%20EB%202022%20FINAL_8-15-22.pdf) and [Bone Fracture](https://humanresearchroadmap.nasa.gov/evidence/reports/Bone%20Fracture%20Evidence%20Report_07-18-2024.pdf) were found, however PDFs were not available through the used verification tool. Therefore, cards on vision and bones rely on verified HRP pages and do not attribute unverified claims to these two reports.

## Evaluated Additional Sources

- [NASA Environmental Data App](https://visualization.osdr.nasa.gov/eda/) shows datasets RR/APEX/VEG and API interface. For a specific series in this verification, the file, units, frequency, and location of the instrument are not confirmed. Cannot mix experimental habitat environment and living section; import is postponed until the selected series is verified.
- [NASA Life Sciences Portal](https://nlsp.nasa.gov/) opens but does not provide readable content through the available tool. No confirmed free file with individual crew data and its access conditions. Adapter is possible after confirmation of a specific dataset.
- [NASA CCMC DONKI](https://ccmc.gsfc.nasa.gov/tools/DONKI/) contains space weather events and API. NASA refers to current information as quality for prototypes/research; addresses were changed on 30.09.2026. Event is not equal to human dose. For autonomous warning, a verified freshness of arrival would be required, which the offline demo does not have. Therefore, DONKI is not included in the personal assessment.

When adding cards to the executable search, save the path to the JSON object, the original URL, and the section. In the query to Qwen, pass only the selected cards, maintaining the context limitation. Scientific references are needed for verifying claims; the application's work with local materials should not require connecting to the source site.
