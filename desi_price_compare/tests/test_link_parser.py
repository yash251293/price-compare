import pytest
import requests
from unittest.mock import patch, MagicMock, ANY # Ensure ANY is imported
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

# Sample HTML for a final Amazon product page (simplified)
FINAL_PRODUCT_PAGE_HTML_AMZN_IN_TITLE_ONLY = """
<!DOCTYPE html>
<html lang="en-in">
<head>
    <meta charset="utf-g">
    <title>Philips India's No.1 Men's Trimmer | Self Sharpening Blades | Single Stroke Grooming I 9 in1 Face, Nose and Body I 2+1* year warranty | Powerful motor | No Oil Needed I 60 min runtime I MG3710/65 : Amazon.in: Health & Personal Care</title>
</head>
<body>
    <h1>Product Page</h1>
    <p>Some details about the Philips Trimmer.</p>
</body>
</html>
"""


@patch('requests.get')
def test_extract_og_title_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = VALID_OG_HTML.encode('utf-8')
    mock_response.text = VALID_OG_HTML # For consistency if text is checked
    mock_response.url = "http://example.com/og_title"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/og_title")
    assert title == "OG Title Exists"
    mock_get.assert_called_once_with("http://example.com/og_title", headers=ANY, timeout=ANY, allow_redirects=ANY)

@patch('requests.get')
def test_extract_html_title_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = VALID_HTML_TITLE_ONLY.encode('utf-8')
    mock_response.text = VALID_HTML_TITLE_ONLY
    mock_response.url = "http://example.com/html_title"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/html_title")
    assert title == "HTML Page Title Only"
    mock_get.assert_called_once_with("http://example.com/html_title", headers=ANY, timeout=ANY, allow_redirects=ANY)

@patch('requests.get')
def test_extract_no_title_found(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = NO_TITLE_HTML.encode('utf-8')
    mock_response.text = NO_TITLE_HTML
    mock_response.url = "http://example.com/no_title"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/no_title")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/no_title", headers=ANY, timeout=ANY, allow_redirects=ANY)

@patch('requests.get')
def test_requests_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Test network error")

    title = extract_product_title("http://example.com/network_error")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/network_error", headers=ANY, timeout=ANY, allow_redirects=ANY)

@patch('requests.get')
def test_http_error_status_code(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.content = "Not Found".encode('utf-8')
    mock_response.text = "Not Found"
    mock_response.url = "http://example.com/not_found"
    mock_response.raise_for_status = MagicMock(side_effect=requests.exceptions.HTTPError("404 Client Error", response=mock_response))
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/not_found")
    assert title is None
    mock_get.assert_called_once_with("http://example.com/not_found", headers=ANY, timeout=ANY, allow_redirects=ANY)

def test_empty_url():
    # This test doesn't use requests.get directly if the URL is empty and caught by the function.
    # extract_product_title now has an initial check for empty URL.
    title = extract_product_title("")
    assert title is None

@patch('requests.get')
def test_malformed_url_handled_by_requests(mock_get):
    # This tests if requests.get itself raises an error for a malformed URL,
    # and that our function handles that by returning None.
    mock_get.side_effect = requests.exceptions.InvalidURL("Invalid URL 'htp://example.com'")
    title = extract_product_title("htp://example.com") # Malformed URL
    assert title is None
    mock_get.assert_called_once_with("htp://example.com", headers=ANY, timeout=ANY, allow_redirects=ANY)


@patch('requests.get')
def test_title_with_leading_trailing_spaces(mock_get):
    html_with_spaces = """
    <html><head><meta property="og:title" content="  Spaced Title  "></head></html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_with_spaces.encode('utf-8')
    mock_response.text = html_with_spaces
    mock_response.url = "http://example.com/spaced_title"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title("http://example.com/spaced_title")
    assert title == "Spaced Title" # .strip() is used in link_parser
    mock_get.assert_called_once_with("http://example.com/spaced_title", headers=ANY, timeout=ANY, allow_redirects=ANY)


@patch('requests.get')
def test_extract_title_from_shortened_amazon_url(mock_get):
    # This test simulates a shortened amzn.in URL which redirects to a full product page.
    # It specifically tests the scenario where the final page has no usable og:title,
    # and the correct, detailed product title is extracted from the HTML <title> tag.
    # This matches the behavior observed for the Philips Trimmer link (e.g., https://amzn.in/d/4UrxwQU).
    short_url = "https://amzn.in/d/1acVKXm" # Using the original test shortlink, outcome is same type
    final_url = "https://www.amazon.in/dp/B09V7GM5M8"
    expected_title = "Philips India's No.1 Men's Trimmer | Self Sharpening Blades | Single Stroke Grooming I 9 in1 Face, Nose and Body I 2+1* year warranty | Powerful motor | No Oil Needed I 60 min runtime I MG3710/65 : Amazon.in: Health & Personal Care"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = FINAL_PRODUCT_PAGE_HTML_AMZN_IN_TITLE_ONLY.encode('utf-8')
    mock_response.text = FINAL_PRODUCT_PAGE_HTML_AMZN_IN_TITLE_ONLY
    mock_response.url = final_url
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title(short_url)

    assert title == expected_title
    mock_get.assert_called_once_with(
        short_url,
        headers=ANY,
        timeout=ANY,
        allow_redirects=True
    )

@patch('requests.get')
def test_extract_title_from_url_with_og_title_preference(mock_get):
    test_url = "https://example.com/product-with-og"
    html_with_og_and_regular_title = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="Preferred OpenGraph Title">
        <title>Less Preferred HTML Title</title>
    </head>
    <body></body>
    </html>
    """
    expected_og_title = "Preferred OpenGraph Title"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_with_og_and_regular_title.encode('utf-8')
    mock_response.text = html_with_og_and_regular_title
    mock_response.url = test_url
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title(test_url)
    assert title == expected_og_title
    mock_get.assert_called_once_with(
        test_url, headers=ANY, timeout=ANY, allow_redirects=True
    )

@patch('requests.get')
def test_extract_title_url_missing_scheme(mock_get):
    url_no_scheme = "www.example.com/productpage"
    url_with_scheme = "https://www.example.com/productpage" # Function prepends https
    expected_title = "Example Product Title"

    sample_html = f"<html><head><title>{expected_title}</title></head><body></body></html>"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = sample_html.encode('utf-8')
    mock_response.text = sample_html
    mock_response.url = url_with_scheme
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    title = extract_product_title(url_no_scheme)
    assert title == expected_title
    mock_get.assert_called_once_with(
        url_with_scheme,
        headers=ANY,
        timeout=ANY,
        allow_redirects=True
    )

# Comments for running tests can be removed or kept at the very end of the file.
# For example:
# To run these tests:
# Ensure you are in the root directory of the project (e.g., parent of desi_price_compare)
# And run: pytest
# Or from within desi_price_compare directory: pytest tests/test_link_parser.py
# (Adjust PYTHONPATH if necessary, e.g., export PYTHONPATH=.:$PYTHONPATH from root)
