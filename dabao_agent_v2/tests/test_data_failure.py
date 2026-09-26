import httpx
import pytest

from config import strategy_config as cfg
from core.cancellation import CancellationToken
from services.logging_service import TaskLogger
from stock.eastmoney_client import EastmoneyClient


def test_data_failure_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cfg, "HTTP_RETRIES", 0)
    client = EastmoneyClient(TaskLogger(), CancellationToken())
    client.client.close()
    client.client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(503, request=request)))
    with pytest.raises(RuntimeError, match="连续失败"):
        client.get_json("https://example.test", {}, "测试接口")
    client.close()

