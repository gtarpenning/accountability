import pytest
from datetime import datetime
from accountability.rh_types import (
    convert_dict_to_typed_dict,
    PercentageDate,
    Holding,
    EquityHistorical,
    BankTransfer,
)


def test_convert_percentage_date():
    data = {"date": "2024-01-01T00:00:00Z", "percentage": 0.05}
    result = convert_dict_to_typed_dict(data, PercentageDate)
    assert isinstance(result["date"], datetime)
    assert result["percentage"] == 0.05


def test_convert_holding():
    data = {
        "price": 100.0,
        "quantity": 10.0,
        "average_buy_price": 90.0,
        "equity": 1000.0,
        "equity_change": 100.0,
        "percent_change": 0.1,
        "percentage": 0.1,
        "name": "Test Stock",
        "id": "test_id",
        "pe_ratio": 15.0,
        "type": "stock",
        "intraday_percent_change": 0.02,
    }
    result = convert_dict_to_typed_dict(data, Holding)
    assert result["price"] == 100.0
    assert result["name"] == "Test Stock"


def test_convert_equity_historical():
    data = {
        "adjusted_open_equity": 1000.0,
        "adjusted_close_equity": 1100.0,
        "open_equity": 1000.0,
        "close_equity": 1100.0,
        "open_market_value": 1000.0,
        "close_market_value": 1100.0,
        "begins_at": "2024-01-01T00:00:00Z",
        "net_return": 100.0,
        "session": "reg",
    }
    result = convert_dict_to_typed_dict(data, EquityHistorical)
    assert result["close_equity"] == 1100.0
    assert isinstance(result["begins_at"], datetime)


def test_convert_bank_transfer():
    data = {
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
    result = convert_dict_to_typed_dict(data, BankTransfer)
    assert result["amount"] == 1000.0
    assert result["direction"] == "deposit"
    assert isinstance(result["created_at"], datetime)
