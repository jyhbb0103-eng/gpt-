import pytest

from core.cancellation import CancellationToken, TaskCancelled


def test_cancellation_flag() -> None:
    token = CancellationToken()
    token.cancel()
    with pytest.raises(TaskCancelled):
        token.raise_if_cancelled()

