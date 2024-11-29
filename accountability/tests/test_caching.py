import pytest
import time
from unittest.mock import patch, MagicMock
from caching import cache_result
from datetime import datetime

@pytest.fixture
def setup_database():
    # This could create a temporary test database
    yield "test_cache.db"
    # Cleanup could go here

def test_cache_result_decorator(setup_database):
    call_count = 0
    
    @cache_result(table_name="test_cache", ttl_seconds=1)
    def test_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # First call should execute the function
    result1 = test_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call should use cached result
    result2 = test_function(5)
    assert result2 == 10
    assert call_count == 1
    
    # Wait for cache to expire
    time.sleep(1.1)
    
    # This call should execute the function again
    result3 = test_function(5)
    assert result3 == 10
    assert call_count == 2

def test_cache_with_datetime():
    @cache_result(table_name="test_datetime_cache", ttl_seconds=1)
    def test_function():
        return {"date": datetime.now()}
    
    result1 = test_function()
    assert isinstance(result1["date"], datetime)
    
    # Second call should return cached result
    result2 = test_function()
    assert isinstance(result2["date"], datetime)
    assert result1["date"] == result2["date"] 