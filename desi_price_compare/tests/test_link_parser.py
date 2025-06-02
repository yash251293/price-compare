import pytest
import requests
from unittest.mock import patch, MagicMock
from desi_price_compare.link_parser import extract_product_title

# Test data
VALID_OG_HTML = """
<html>
<head>
    <meta property="og:title" content="OG Title Exists">
    <title>HTML Page Title</title>
</head>
<body></body>
</html>
"""

VALID_HTML_TITLE_ONLY = """
<html>
<head>
    <title>HTML Page Title Only</title>
</head>
<body></body>
</html>
"""

NO_TITLE_HTML = """
<html>
<head></head>
<body><p>No title here</p></body>
</html>
"""

@patch('requests.get')
def test_extract_og_title_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = VALID_OG_HTML.encode('utf-8')
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/og_title")
    assert title == "OG Title Exists"
    mock_get.assert_called_once_with("http://example.com/og_title", headers={'User-Agent': 'Mozilla/5.0'})

@patch('requests.get')
def test_extract_html_title_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = VALID_HTML_TITLE_ONLY.encode('utf-8')
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/html_title")
    assert title == "HTML Page Title Only"
    mock_get.assert_called_once_with("http://example.com/html_title", headers={'User-Agent': 'Mozilla/5.0'})

@patch('requests.get')
def test_extract_no_title_found(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = NO_TITLE_HTML.encode('utf-8')
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/no_title")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/no_title", headers={'User-Agent': 'Mozilla/5.0'})

@patch('requests.get')
def test_requests_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Test network error")

    title = extract_product_title("http://example.com/network_error")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/network_error", headers={'User-Agent': 'Mozilla/5.0'})

@patch('requests.get')
def test_http_error_status_code(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.content = "Not Found".encode('utf-8')
    # Mock raise_for_status to simulate an HTTPError being raised by it
    mock_response.raise_for_status = MagicMock(side_effect=requests.exceptions.HTTPError("404 Client Error"))
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/not_found")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/not_found", headers={'User-Agent': 'Mozilla/5.0'})

def test_empty_url():
    # requests.get would typically raise an InvalidSchema or MissingSchema error for "" or " "
    # For an empty string, our function might not even call requests.get if we add a check,
    # but current link_parser.py doesn't have such a check before calling requests.get.
    # If requests.get is called with an empty string, it raises an exception.
    # Let's assume the current behavior is that requests.get is called and raises an error.
    with patch('requests.get', side_effect=requests.exceptions.MissingSchema("No schema supplied")):
        title = extract_product_title("")
        assert title is None

def test_malformed_url_handled_by_requests():
    # e.g. "htp://example.com" or a URL with characters that requests might reject.
    # This often results in requests.exceptions.InvalidURL
    with patch('requests.get', side_effect=requests.exceptions.InvalidURL("Invalid URL 'htp://example.com'")):
        title = extract_product_title("htp://example.com") # Malformed URL
        assert title is None

@patch('requests.get')
def test_title_with_leading_trailing_spaces(mock_get):
    html_with_spaces = """
    <html><head><meta property="og:title" content="  Spaced Title  "></head></html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_with_spaces.encode('utf-8')
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/spaced_title")
    assert title == "Spaced Title" # .strip() is used in link_parser

# It might be good to also test if the User-Agent header is correctly passed,
# which is already implicitly done by mock_get.assert_called_once_with(...) in the first test.

# To run these tests (from the /app directory):
# Ensure __init__.py exists in desi_price_compare and desi_price_compare/tests if needed for discovery.
# PYTHONPATH=. pytest desi_price_compare/tests/test_link_parser.py
