import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

client = TestClient(app)


@pytest.fixture
def mock_rh_login():
    with patch("robin_stocks.robinhood.login") as mock:
        yield mock


@pytest.fixture
def mock_get_historical():
    with patch("rh_api.get_historical_portfolio_percentage") as mock:
        yield mock


@pytest.fixture
def mock_get_ytd():
    with patch("rh_api.get_running_ytd_percentage") as mock:
        yield mock


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
