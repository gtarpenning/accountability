import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from accountability.rh_api import (
    _get_historical_portfolio_percentage,
    get_historical_portfolio,
    get_bank_transfers,
    get_running_ytd_percentage,
)


@pytest.fixture
def sample_historical_data():
    return [
        {
            "close_equity": 1000.0,
            "begins_at": datetime(2024, 1, 1),
        },
        {
            "close_equity": 1100.0,
            "begins_at": datetime(2024, 1, 2),
        },
    ]


def test_get_historical_portfolio_percentage(sample_historical_data):
    result = _get_historical_portfolio_percentage(sample_historical_data)
    assert len(result) == 2
    assert result[1]["percentage"] == pytest.approx(0.1)  # 10% increase


@patch("robin_stocks.robinhood.get_historical_portfolio")
def test_get_historical_portfolio(mock_get_historical):
    mock_data = {
        "equity_historicals": [
            {
                "adjusted_open_equity": 1000.0,
                "adjusted_close_equity": 1100.0,
                "open_equity": 1000.0,
                "close_equity": 1100.0,
                "begins_at": "2024-01-01T00:00:00Z",
                "open_market_value": 1000.0,
                "close_market_value": 1100.0,
                "net_return": 100.0,
                "session": "reg",
            }
        ]
    }
    mock_get_historical.return_value = mock_data

    result = get_historical_portfolio()
    assert len(result) == 1
    assert result[0]["close_equity"] == 1100.0


@patch("robin_stocks.robinhood.get_bank_transfers")
def test_get_bank_transfers(mock_get_transfers):
    mock_data = [
        {
            "id": "test_id",
            "url": "test_url",
            "ref_id": "test_ref",
            "cancel": None,
            "ach_relationship": "test_ach",
            "account": "test_account",
            "amount": 1000.0,
            "direction": "deposit",
            "state": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]
    mock_get_transfers.return_value = mock_data

    result = get_bank_transfers()
    assert len(result) == 1
    assert result[0]["amount"] == 1000.0
