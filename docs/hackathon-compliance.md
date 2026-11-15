# Compliance Check Submission — 15.11.2026

## Checked in the Repository

| Requirement | Implementation in ASTRA | Status |
|---|---|---|
| Respond to the selected track | The product collects health metrics, stores personal dynamics, shows status, and helps choose an action; this directly answers the [astronaut health monitoring track](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/). | Ready |
| Use official data or resources on the subject | The product includes 16 local scientific cards, 84 archived radiation environment points, and 532 laboratory records. Source, version, date of acquisition, unit, and limitation are stored with the data; origin is described in the [source registry](space-science-sources.md). | Ready |
| Give the astronaut the ability to assess status and act | There are profile measurements, trends, signal forecast, mission context, chat with clarifying questions, recommendations, and scenarios. Archived data do not mix with personal data. | Ready |
| Autonomous operation | API, database, model, cards, and data snapshots work locally; internet is needed only to open a link to the source. Instructions: [offline-demo.md](offline-demo.md). | Ready |
| Verifiability of scientific claims | Names of organizations and campaigns are not used as formatting or free text. They are displayed only within links to sources. Model responses are checked for unconfirmed numbers, time, personal dose, and source names in plain text. | Ready |
| Working prototype | Backend tests, production interface build, browser scenario, and conversation through a real local model are included in the check before presentation. | Ready |
| English description | The project description and launch instructions are maintained in the repository README. | Ready as a draft |
| Open licensing and attribution | Original project materials use [Apache-2.0](../LICENSE). External software, model weights, publications, and the packaged research datasets are identified in [third-party notices](../THIRD_PARTY_NOTICES.md); source metadata and checksums are in the [manifest](../backend/data/research/manifest.json). | Code and source documentation ready; confirm rights in the reference image used for the AI-generated illustration before public submission. |
| Public Demonstration | There is a script in the repository, but a public link to the video/slides is created by the project owner outside of the code. | Requires team action |
| Public link to code | The local folder is ready; visibility of the remote repository and the link are checked by the project owner. | Requires team action |

## Compliance with Evaluation Criteria

- **Impact:** Autonomous health review reduces dependency on immediate response from Earth.
- **Creativity:** A single local interface combines personal dynamics, mission context, scientific data, and dialogue.
- **Validity:** Each scientific claim is linked to a local card and original reference; the environmental archive does not provide personal dose.
- **Relevance:** Both verbs of the task — collect metrics and help assess condition/action — are implemented.
- **Presentation:** There is a unified dark interface, three contrasting demo profiles, and a short reproducible demonstration scenario.

Criteria are aligned with the published event page; final fields and deadline must be checked on the team's page. [Official event page and submission](https://www.spaceappschallenge.org/2026/).

## What Cannot Be Verified from the Repository

Before submission, the team owner must check:

1. All participants are registered and part of one team/local event; the team does not exceed six people.
2. In the Project Tab, the correct track is selected and all required fields are filled in English.
3. The code link opens without authentication.
4. Demo — a public video link no longer than 30 seconds **or** a presentation no more than seven slides, including the title slide.
5. For non-English videos, English subtitles are added; slides are completed in English.
6. The project is submitted by **15 November 2026, 23:59 local time of the selected event**; separately checked for an earlier local deadline, if announced by the local organizer.
7. On the submission page, participation in judging is marked and current participant terms are accepted.
8. Confirm that the supplied anatomical reference image may be used for the published generated illustration; the original reference image is not in this repository.

This is not software defects: team data, public links, form flags, and actual submission cannot be reliably changed from the local project.
