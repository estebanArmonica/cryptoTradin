import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from api import app

client = TestClient(app)

# Mock para CoinGeckoAPI
@pytest.fixture
def mock_coingecko():
    with patch('main.cg') as mock:
        yield mock

def test_get_ping_success(mock_coingecko):
    mock_coingecko.ping.return_value = {"gecko_says": "(V3) To the Moon!"}
    
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {
        "status": True,
        "message": "Conexión exitosa con CoinGecko"
    }

def test_get_ping_failure(mock_coingecko):
    mock_coingecko.ping.return_value = None
    
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {
        "status": False,
        "message": "Error al conectar con CoinGecko"
    }

def test_get_categories(mock_coingecko):
    mock_data = [{"category_id": "1", "name": "DeFi"}]
    mock_coingecko.get_coins_categories_list.return_value = mock_data
    
    response = client.get("/categories")
    assert response.status_code == 200
    assert response.json() == [{"id": "1", "name": "DeFi"}]

def test_get_prices(mock_coingecko):
    mock_data = {"bitcoin": {"usd": 50000, "eur": 42000}}
    mock_coingecko.get_price.return_value = mock_data
    
    response = client.get("/prices?coin_ids=bitcoin&vs_currencies=usd,eur")
    assert response.status_code == 200
    assert response.json() == {
        "coin_id": "bitcoin",
        "prices": {"bitcoin": {"usd": 50000, "eur": 42000}}
    }

def test_get_coin_list(mock_coingecko):
    mock_data = [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]
    mock_coingecko.get_coins_list.return_value = mock_data
    
    response = client.get("/coins")
    assert response.status_code == 200
    assert response.json() == [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}]

def test_api_error_handling(mock_coingecko):
    mock_coingecko.get_coins_categories_list.side_effect = Exception("API Error")
    
    response = client.get("/categories")
    assert response.status_code == 500
    assert "API Error" in response.json()["detail"]