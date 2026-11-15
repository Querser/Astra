"""Local, source-linked location context; never infer a person's dose from it."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models import CrewMember


@lru_cache(maxsize=1)
def location_catalog() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_MISSION_LOCATIONS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def mission_context_for(crew: CrewMember) -> dict[str, Any] | None:
    location = crew.mission_location
    facts = location_catalog()["locations"].get(location)
    if facts is None:
        return None
    return {
        "location": location,
        "name": facts["name_ru"],
        "phase": crew.mission_phase,
        "habitat": crew.habitat,
        "gravity": facts["gravity_ru"],
        "external_atmosphere": facts["external_atmosphere_ru"],
        "radiation": facts["radiation_ru"],
        "sources": facts["sources"],
        "status": "public_location_context; fictional_profile_assignment",
    }
