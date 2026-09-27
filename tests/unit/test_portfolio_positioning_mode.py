import pytest
from fastapi import HTTPException

from backend.jobs.executor import _validate_portfolio_positioning_mode


def test_portfolio_positioning_defaults_to_deep() -> None:
    assert _validate_portfolio_positioning_mode(None) == "deep"
    assert _validate_portfolio_positioning_mode("deep") == "deep"


def test_portfolio_positioning_rejects_retired_fast_mode() -> None:
    with pytest.raises(HTTPException) as raised:
        _validate_portfolio_positioning_mode("fast")

    assert raised.value.status_code == 400
    assert raised.value.detail == "Portfolio positioning is deep-only; fast mode has been retired."
