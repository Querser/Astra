"""Schema and provenance checks for locally packaged primary-source cards."""

import json
from pathlib import Path


CARDS_PATH = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_SPACE_SCIENCE.json"


def test_space_science_cards_have_traceable_sources():
    catalog = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    assert catalog["kind"] == "general_scientific_reference"
    assert catalog["retrieved_at"]
    cards = catalog["cards"]
    assert len(cards) >= 12
    assert len({card["id"] for card in cards}) == len(cards)
    required = {"id", "topic", "title_ru", "source", "evidence_population",
                "observations", "required_inputs", "units", "measurement_conditions",
                "supported_interpretation", "missing_inputs", "practical_actions",
                "limitations", "keywords"}
    for card in cards:
        assert required <= card.keys(), card["id"]
        assert card["source"]["organization"]
        assert card["source"]["title"]
        assert card["source"]["url"].startswith("https://")
        assert card["source"]["section"]
        assert card["supported_interpretation"]
        assert card["limitations"]
        assert card["keywords"]


def test_five_hazards_and_engineering_context_are_distinct():
    cards = {card["id"]: card for card in json.loads(CARDS_PATH.read_text(encoding="utf-8"))["cards"]}
    assert {"HRP.HAZARD.RADIATION", "HRP.HAZARD.ISOLATION", "HRP.HAZARD.DISTANCE",
            "HRP.HAZARD.GRAVITY", "HRP.HAZARD.HABITAT"} <= cards.keys()
    co2 = cards["STD3001.V2.6004"]
    assert co2["source"]["version"] == "Rev F"
    assert "[V2 6004]" in co2["source"]["section"]
    assert co2["units"] == ["mmHg"]
    assert "hour" in " ".join(co2["measurement_conditions"])
    assert cards["CSA.RADIATION.CANS"]["evidence_population"] == "instrument_development"
