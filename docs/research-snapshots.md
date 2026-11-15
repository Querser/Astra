# Local NASA Research Images

The project contains two small **archival** CSVs. Original files and SHA-256 hashes are specified in `backend/data/research/manifest.json`. They are checked before import and during reading. The application uses a local copy; no network access is needed at startup.

| Set | Source | Content | Limitation |
|---|---|---|---|
| RadLab DosTel1 | [NASA RadLab Data API](https://visualization.osdr.nasa.gov/radlab/gui/data-api/), query in manifest; portal 1.1.2, obtained 14.11.2026 | 84 instrument measurements of DosTel1 in the Columbus module of the ISS, from 01.04.2022 23:00 to 02.04.2022 01:04 according to CSV timestamps. Absorbed dose rate in µGy/hour; equivalent dose rate field in µSv/hour is present, but all 84 values are missing. Between timestamps 3–1055 seconds, median 100 seconds. | CSV does not specify time zone; measured environment of the device, not personal dose. Cannot infer equivalent dose from an empty field or equate it to absorbed dose. |
| OSD-575 | [NASA OSDR OSD-575](https://osdr.nasa.gov/bio/repo/data/studies/OSD-575), [metadata](https://osdr.nasa.gov/osdr/data/osd/meta/575), version 3, obtained 14.11.2026 | Original transformed CMP CSV: 28 serum samples, four anonymized participants from Inspiration4, 19 analysts × 28 samples = 532 records, of which 23 have no value. Points L−92, L−44, L−3 before flight and R+1, R+45, R+82, R+194 after. | It is not a series of life signs of the ASTRA crew. Reference limits belong to the original laboratory file and method, and are not individual cosmic norms. |

Public processed human data and terms of use are described in [OSDR FAQ](https://science.nasa.gov/reference/osdr-faq/) and [OSDR Terms](https://science.nasa.gov/reference/osdr-help-terms-and-conditions/). Participant identifiers `C001`–`C004` are stored only in separate research tables and are not linked to fictional crew profiles.

Import into an explicitly defined **test** database from the `backend` catalog:

```powershell
..\.venv\Scripts\python.exe import_research_snapshots.py --database "$env:TEMP\astra_research_demo.sqlite3"
```

Repeating the command is idempotent: already imported records are identified by a stable key, new records are not duplicated. The command does not download data. To update the snapshot, you need to first separately check the official API, version, file names, units, missing values, and permissions; then replace the CSV and its SHA-256 in the manifest. Importing another version will require a separate dataset key to avoid mixing data.

API after import: `/api/v1/research/radlab` and `/api/v1/research/osd-575`. Brief local information is passed to Qwen only on relevant questions, with a clear note that the device and participants do not belong to the selected profile.
