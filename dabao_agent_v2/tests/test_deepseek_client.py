import httpx

from config.settings import Settings
from llm.deepseek_client import DeepSeekClient, MISSING_KEY_MESSAGE


def test_deepseek_mock() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "你好"}}]})
    settings = Settings(DEEPSEEK_API_KEY="test-key", _env_file=None)
    assert DeepSeekClient(settings, httpx.MockTransport(handler)).chat([{"role": "user", "content": "hi"}]) == "你好"


def test_missing_key_message() -> None:
    settings = Settings(_env_file=None)
    try:
        DeepSeekClient(settings).chat([])
    except ValueError as exc:
        assert str(exc) == MISSING_KEY_MESSAGE

