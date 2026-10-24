import pytest

from docs_copilot.settings import Settings


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCS_COPILOT_EMBEDDING_DIM", "768")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert s.embedding_dim == 768
    assert s.openai_api_key is not None
    assert s.openai_api_key.get_secret_value() == "sk-test"
    assert "sk-test" not in repr(s)  # secrets never leak into logs
