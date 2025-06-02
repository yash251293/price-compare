import pytest
from unittest.mock import patch, MagicMock
import os # For path joining
import requests # For requests.exceptions
from bs4 import BeautifulSoup # For potentially creating soup objects if needed

# Adjust import path based on your project structure
# Assuming tests are run from the root directory where desi_price_compare is a package
from desi_price_compare.amazon_api import _scrape_amazon_search_results_page, search_amazon_products

# Path to the sample HTML file
SAMPLE_HTML_PATH = os.path.join(os.path.dirname(__file__), 'sample_amazon_in_search.html')

@pytest.fixture
def mock_requests_get_fixture(): # Renamed to avoid conflict with requests.get if used directly
    with patch('requests.get') as mock_get:
        yield mock_get

def load_sample_html():
    with open(SAMPLE_HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def test_scrape_amazon_successful_extraction(mock_requests_get_fixture):
    sample_html_content = load_sample_html()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = sample_html_content.encode('utf-8') # Encode to bytes
    mock_response.text = sample_html_content # Keep a string version for 'captcha' checks etc.
    mock_response.raise_for_status = MagicMock() # Ensure raise_for_status does nothing for this successful test
    mock_requests_get_fixture.return_value = mock_response

    # We are testing the internal function directly
    # _scrape_amazon_search_results_page also calls time.sleep, we can patch it if we want to speed up tests
    with patch('time.sleep', return_value=None) as _: # Patch time.sleep to avoid delays
        products = _scrape_amazon_search_results_page("test query for successful extraction")

    assert len(products) == 3 # Expecting 3 valid products from the sample
                               # Product 2 is missing price and should be skipped.
                               # Product 1, 3, 4 should be parsed.

    # Product 1
    assert products[0]['title'] == "Test Product 1: Cool Gadget"
    assert products[0]['price'] == "₹1,999.00"
    assert products[0]['image_url'] == "https://m.media-amazon.com/images/I/image1.jpg"
    assert products[0]['product_url'] == "https://www.amazon.in/dp/B080X4DRG8/ref=sr_1_1"

    # Product 3 (Product 2 is skipped due to missing price)
    assert products[1]['title'] == "Test Product 3: Full Data"
    assert products[1]['price'] == "₹2,499.50"
    assert products[1]['image_url'] == "https://m.media-amazon.com/images/I/image3.jpg"
    assert products[1]['product_url'] == "https://www.amazon.in/dp/B0ABCDEFGH/ref=sr_1_3"

    # Product 4 (Alternative Structure)
    assert products[2]['title'] == "Alternative Product 4: Test With Alt Structure"
    assert products[2]['price'] == "₹799.00"
    assert products[2]['image_url'] == "https://m.media-amazon.com/images/I/image4_alt.jpg"
    assert products[2]['product_url'] == "https://www.amazon.in/Alternative-Product-4-Link/dp/B0ALTCONT1/"

    mock_requests_get_fixture.assert_called_once() # Check that requests.get was called

def test_scrape_amazon_request_exception(mock_requests_get_fixture):
    mock_requests_get_fixture.side_effect = requests.exceptions.RequestException("Test network error")
    with patch('time.sleep', return_value=None) as _:
        products = _scrape_amazon_search_results_page("test query for request exception")
    assert len(products) == 0

def test_scrape_amazon_http_error(mock_requests_get_fixture):
    mock_response = MagicMock()
    mock_response.status_code = 503 # Simulate a server error
    mock_response.text = "Service Unavailable or CAPTCHA"
    # Configure raise_for_status to actually raise an HTTPError
    http_error = requests.exceptions.HTTPError("503 Server Error", response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    mock_requests_get_fixture.return_value = mock_response

    with patch('time.sleep', return_value=None) as _:
        products = _scrape_amazon_search_results_page("test query for http error")
    assert len(products) == 0

def test_scrape_amazon_captcha_detected(mock_requests_get_fixture):
    sample_html_content = "<html><body>CAPTCHA required</body></html>" # Simplified CAPTCHA page
    mock_response = MagicMock()
    mock_response.status_code = 200 # Sometimes CAPTCHA pages return 200
    mock_response.content = sample_html_content.encode('utf-8')
    mock_response.text = sample_html_content
    mock_response.raise_for_status = MagicMock()
    mock_requests_get_fixture.return_value = mock_response

    with patch('time.sleep', return_value=None) as _:
        products = _scrape_amazon_search_results_page("test query for captcha")
    assert len(products) == 0


def test_scrape_amazon_no_products_found_on_page(mock_requests_get_fixture):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"<html><body><h1>No results, just a plain page</h1></body></html>"
    mock_response.text = "<html><body><h1>No results, just a plain page</h1></body></html>"
    mock_response.raise_for_status = MagicMock()
    mock_requests_get_fixture.return_value = mock_response

    with patch('time.sleep', return_value=None) as _:
        products = _scrape_amazon_search_results_page("test query for no products on page")
    assert len(products) == 0

def test_search_amazon_products_empty_title(mock_requests_get_fixture):
    # Test the public search_amazon_products function with an empty title
    # This function also calls _scrape_amazon_search_results_page, which has time.sleep
    with patch('time.sleep', return_value=None) as _: # Patch sleep here too if it were called
        products = search_amazon_products("")
    assert len(products) == 0
    mock_requests_get_fixture.assert_not_called() # Ensure no HTTP request is made for empty title

def test_scrape_amazon_product_limit(mock_requests_get_fixture):
    # Create a dummy HTML with more than 5 products to test the limit
    html_items = ""
    for i in range(10):
        html_items += f"""
        <div data-component-type="s-search-result" data-asin="B0TEST{i}">
          <h2><a class="a-link-normal s-underline-text" href="/dp/B0TEST{i}"><span class="a-text-normal">Test Product {i}</span></a></h2>
          <div class="a-price-section"><span class="a-price"><span class="a-offscreen">₹1{i}.00</span></span></div>
          <div class="s-image-square-aspect"><img class="s-image" src="image{i}.jpg" /></div>
        </div>
        """
    sample_html_content = f"<html><body>{html_items}</body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = sample_html_content.encode('utf-8')
    mock_response.text = sample_html_content
    mock_response.raise_for_status = MagicMock()
    mock_requests_get_fixture.return_value = mock_response

    with patch('time.sleep', return_value=None) as _:
        products = _scrape_amazon_search_results_page("test query for product limit")

    assert len(products) == 5 # Scraper should limit to 5 products
    assert products[4]['title'] == "Test Product 4" # Check the last product is as expected
