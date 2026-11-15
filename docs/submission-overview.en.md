# ASTRA — project overview draft

ASTRA is an offline-first demonstration for astronaut health monitoring during long missions. A crew member records measurements, collection conditions, symptoms and mission context in a local application. The interface shows the individual history and descriptive changes. A locally hosted Qwen3:8b assistant receives only the selected crew profile, a bounded set of relevant local knowledge cards, and the latest conversation facts. It can ask follow-up questions and explain the available evidence in Russian without a runtime internet connection.

Official challenge resources inform the local cards on radiation, altered gravity, isolation, closed habitats, distance from Earth, sleep, cardiovascular adaptation and SANS. Additional linked official articles inform the radiation-monitoring and medical-autonomy explanations. A small [NASA RadLab snapshot](https://visualization.osdr.nasa.gov/radlab/gui/overview/) shows 84 historical absorbed-dose-rate readings from an instrument near an orbital module; it is environmental instrument data, not a crew member's dose. A separately labeled [NASA OSD-575 research view](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575/) shows 532 serum laboratory observations from four deidentified research participants. Neither dataset is attached to fictional crew identities. Every displayed source has its original URL, version when available, retrieval date, units and measurement limitations.

ASTRA's numerical forecasts are reproducible statistical continuations of personal measurement series. The assistant explains those results; it does not train on the imported research participants or infer treatment effects from them. This demonstration has not been clinically validated and does not make a fitness-for-duty decision. The current UI uses manual measurement entry. Future sensor adapters are an explicit extension point rather than a claimed live feed.

## Seven-slide demo storyboard

The [current Space Apps Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) allows a slide demo of up to seven slides, including its title slide. The following draft stays within that limit. Use English slides with legible screenshots from the verified running application. Team identity and a public project URL must be added by the team before submission.

1. **ASTRA / the challenge.** Identify the team and the challenge. Show the dashboard and state the need for health monitoring when communication and expert support are delayed.
2. **Local measurement workflow.** Show manual entry with time, device or method, rest/activity and body site. Show that the selected crew profile owns its history.
3. **Personal change and forecasts.** Show a recorded series, a visible change and the actual 24/72/168-hour statistical forecast method and error estimate. Label this as a signal forecast.
4. **Local assistant with cited knowledge.** Ask a sleep/fatigue question; show a relevant source card, follow-up question and source details. State that the selected language model runs locally.
5. **Historical radiation context.** Show the RadLab DosTel1 ISS graph with its 2022 interval and µGy/hour unit. Explain that equivalent dose rate is missing in this snapshot and the series is not an individual dose.
6. **Separate human research view.** Show OSD-575 participant/analyte history with original units and mission-relative L/R samples, clearly separated from fictional crew records.
7. **Architecture and limits.** Diagram: manual profile data + bundled sourced cards + packaged public snapshots → local API/SQLite → bounded retrieval and local model → source-attributed UI. State no live sensor feed and no clinical validation; provide a public link to the working code/demo.

This is a technical overview draft. Complete the separate submission fields and event requirements in the later publication task.
