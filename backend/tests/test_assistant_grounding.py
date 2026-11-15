"""The optional local model must not add facts or send records to a remote URL."""

import json

from app.assistant import LocalAssistant


def test_remote_ollama_url_is_rejected_before_request(monkeypatch) -> None:
    import app.assistant as assistant_module

    def unexpected_request(*_args, **_kwargs):
        raise AssertionError("Remote model must not receive the request")

    monkeypatch.setattr(assistant_module, "urlopen", unexpected_request)
    status, answer = LocalAssistant(
        base_url="https://example.org:11434", enable_experimental=True
    ).explain({"facts": []}, None)
    assert status == "unavailable"
    assert "loopback" in answer


def test_model_cannot_add_claim_even_with_valid_json_and_citation(monkeypatch) -> None:
    import app.assistant as assistant_module

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            reply = {
                "summary": "У космонавта подтверждено заболевание; требуется лечение.",
                "citation": assistant_module.REFERENCE_CITATION,
                "not_a_diagnosis": True,
            }
            return json.dumps({"message": {"content": json.dumps(reply, ensure_ascii=False)}}, ensure_ascii=False).encode("utf-8")

    monkeypatch.setattr(assistant_module, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    status, answer = LocalAssistant(enable_experimental=True).explain(
        {"facts": [{"kind": "reference_review", "metric": "heart_rate", "status": "not_assessed"}]},
        None,
    )
    assert status == "fallback"
    assert "confirmed disease" not in answer.lower()
