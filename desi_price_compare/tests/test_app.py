import pytest
import json
from unittest.mock import patch, MagicMock
import requests # Required for the RequestException test

# Add desi_price_compare to sys.path for sibling imports if not running with `PYTHONPATH=.`
# This is often handled by how pytest discovers and runs tests, or by project structure.
# For this environment, assuming direct execution or pytest handles it.
from desi_price_compare.app import app as flask_app # renamed to avoid conflict with fixture

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # You might need to set specific configurations for testing, e.g., app.config['TESTING'] = True
    # flask_app.config.update({
    #     "TESTING": True,
    # })
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_index_route(client):
    """Test the index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'<form id="product-link-form">' in response.data
    assert b'<h1>Welcome to Desi Price Compare!</h1>' in response.data

# Patching at the location where the names are looked up (i.e., in app.py)
@patch('desi_price_compare.app.search_amazon_products')
@patch('desi_price_compare.app.extract_product_title')
def test_search_success(mock_extract_title, mock_search_amazon, client):
    """Test /search route with successful title extraction and product search."""
    mock_extract_title.return_value = "Test Product Title"
    mock_search_amazon.return_value = [
        {"title": "Test Product 1", "price": "₹100", "image_url": "img1.jpg", "product_url": "url1"},
        {"title": "Test Product 2", "price": "₹200", "image_url": "img2.jpg", "product_url": "url2"}
    ]

    response = client.post('/search', data={'product_link': 'http://example.com/product'})

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'products' in data
    assert len(data['products']) == 2
    assert data['products'][0]['title'] == "Test Product 1"
    mock_extract_title.assert_called_once_with('http://example.com/product')
    mock_search_amazon.assert_called_once_with("Test Product Title")

@patch('desi_price_compare.app.extract_product_title')
def test_search_title_extraction_failure(mock_extract_title, client):
    """Test /search route when title extraction fails."""
    mock_extract_title.return_value = None # Simulate title not found

    response = client.post('/search', data={'product_link': 'http://example.com/invalid_product'})

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert "Could not extract a valid product title" in data['error']
    mock_extract_title.assert_called_once_with('http://example.com/invalid_product')

def test_search_empty_product_link(client):
    """Test /search route with an empty product_link."""
    response = client.post('/search', data={'product_link': ''})

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert "Product link is missing or empty" in data['error']

@patch('desi_price_compare.app.extract_product_title')
def test_search_title_extraction_exception(mock_extract_title, client):
    """Test /search route when extract_product_title raises a RequestException."""
    mock_extract_title.side_effect = requests.exceptions.RequestException("Simulated network error")

    response = client.post('/search', data={'product_link': 'http://example.com/network_issue'})

    assert response.status_code == 500 # As per current app.py error handling for RequestException
    data = json.loads(response.data)
    assert 'error' in data
    assert "Network error while trying to access the product link" in data['error']
    mock_extract_title.assert_called_once_with('http://example.com/network_issue')

@patch('desi_price_compare.app.search_amazon_products')
@patch('desi_price_compare.app.extract_product_title')
def test_search_no_products_found(mock_extract_title, mock_search_amazon, client):
    """Test /search route when products are not found (empty list)."""
    mock_extract_title.return_value = "Existing Product Title"
    mock_search_amazon.return_value = [] # Simulate no products found

    response = client.post('/search', data={'product_link': 'http://example.com/finds_nothing'})

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'products' in data
    assert len(data['products']) == 0
    mock_extract_title.assert_called_once_with('http://example.com/finds_nothing')
    mock_search_amazon.assert_called_once_with("Existing Product Title")

@patch('desi_price_compare.app.extract_product_title') # Patch to prevent actual call
def test_search_unexpected_server_error(mock_extract_title, client):
    """Test /search route with an unexpected error during processing."""
    # Make extract_product_title raise a generic Exception, different from RequestException
    mock_extract_title.side_effect = Exception("Totally unexpected error!")

    response = client.post('/search', data={'product_link': 'http://example.com/cause_generic_error'})

    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    assert "An unexpected server error occurred" in data['error']
    mock_extract_title.assert_called_once_with('http://example.com/cause_generic_error')


# To run these tests (from the /app directory):
# Ensure __init__.py exists in desi_price_compare and desi_price_compare/tests if needed.
# PYTHONPATH=. pytest desi_price_compare/tests/test_app.py
