import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote # More standard than requests.utils.quote

# TODO: Import amazon_paapi and other necessary modules when implementing actual API calls
# from paapi5_python_sdk.api.default_api import DefaultApi
# ... (other PAAPI imports)

# Rate limiting: simple delay between requests to be less aggressive.
# (60 seconds / 10 requests per minute = 6 seconds per request)
REQUEST_INTERVAL = 6

# Placeholder for a more sophisticated rate limiter if needed later
# For now, simple sleep in the scraping function.

def _scrape_amazon_search_results_page(product_title: str) -> list[dict]:
    """
    Scrapes Amazon.in search results for a given product title.
    DEV/TEST ONLY for amazon.in. NOT FOR PRODUCTION.
    User-confirmed permission for dev/test scraping in this specific context.
    Rate limit: Attempts to respect ~10 requests per minute via REQUEST_INTERVAL.
    """
    print(f"Waiting for {REQUEST_INTERVAL} seconds due to rate limiting...")
    time.sleep(REQUEST_INTERVAL) # Simple delay before each request

    search_url = f"https://www.amazon.in/s?k={quote(product_title)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive',
        'DNT': '1', # Do Not Track
        # 'Referer': 'https://www.amazon.in/' # Sometimes helpful
    }

    products_found = []
    try:
        print(f"Scraping Amazon.in for: '{product_title}' using URL: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=15) # Increased timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)

        # It's good to check if CAPTCHA is present
        if "captcha" in response.text.lower() or "api-services-support@amazon.com" in response.text:
            print("CAPTCHA or block page detected. Cannot scrape.")
            return []

        soup = BeautifulSoup(response.content, 'html.parser') # Using built-in html.parser

        # Primary selector for search result items
        search_results_items = soup.find_all('div', {'data-component-type': 's-search-result'})

        # Fallback selector if primary fails (less specific, might grab other things)
        if not search_results_items:
            print("Primary selector 'div[data-component-type=\"s-search-result\"]' failed. Trying fallback...")
            search_results_items = soup.find_all('div', {'data-asin': True, 'class': lambda x: x and 's-result-item' in x.split()})

        if not search_results_items:
            print("No search result items found using known selectors. Page structure might have changed.")
            # print(f"Page content for debugging (first 500 chars): {response.text[:500]}") # Uncomment for debugging
            return []

        for item_count, item in enumerate(search_results_items):
            title, price, image_url, product_url = None, None, None, None

            # Title
            title_element = item.select_one('h2 a.a-link-normal span.a-text-normal')
            if title_element:
                title = title_element.get_text(strip=True)

            # Price
            # Common price pattern: <span class="a-price" data-a-size="xl" data-a-color="base"><span class="a-offscreen">₹<!-- -->1,23,456.00</span>...</span>
            price_element = item.select_one('span.a-price > span.a-offscreen')
            if not price_element: # Try another common price structure if first fails
                price_element = item.select_one('span.a-price-whole') # e.g. <span class="a-price-whole">1,23,456</span>

            if price_element:
                price = price_element.get_text(strip=True)
                # If only whole is found (no symbol), try to get symbol
                if item.select_one('span.a-price-whole') and not any(c in price for c in ['₹', '$', '€', '£']):
                     price_symbol_element = item.select_one('span.a-price-symbol')
                     if price_symbol_element:
                         price = price_symbol_element.get_text(strip=True) + price


            # Image URL
            image_element = item.select_one('img.s-image')
            if image_element:
                image_url = image_element.get('src')

            # Product URL
            # Common link: <a class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal"
            url_element = item.select_one('h2 a.a-link-normal') # More general for the link within h2
            if url_element:
                raw_url = url_element.get('href')
                if raw_url:
                    if not raw_url.startswith('https://www.amazon.in') and raw_url.startswith('/'):
                        product_url = f"https://www.amazon.in{raw_url}"
                    elif raw_url.startswith('https://www.amazon.in'):
                        product_url = raw_url
                    # else: print(f"Skipping relative URL not starting with '/': {raw_url}") # For debugging weird URLs

            if title and price and image_url and product_url:
                products_found.append({
                    "title": title,
                    "price": price,
                    "image_url": image_url,
                    "product_url": product_url
                })

            # print(f"Item {item_count}: Title: {title}, Price: {price}, Image: {bool(image_url)}, URL: {bool(product_url)}") # Debug each item
            if len(products_found) >= 5: # Limit results to 5
                print("Reached limit of 5 products.")
                break

        if not products_found:
            print("No products extracted, though search result items might have been found. Check selectors for title, price, image, URL.")

    except requests.exceptions.HTTPError as http_err:
        # http_err.response is guaranteed to be available for HTTPError
        status_code = http_err.response.status_code
        print(f"HTTP error occurred: {http_err} - Status: {status_code}")
        # print(f"Response content for HTTP error: {http_err.response.text[:500]}") # Uncomment for debugging
        if status_code == 404:
            print("Page not found. Check search URL or product title.")
        # Check response text for captcha, ensuring http_err.response.text exists
        elif status_code == 503 or \
             (hasattr(http_err.response, 'text') and http_err.response.text and 'captcha' in http_err.response.text.lower()):
            print("Amazon might be temporarily blocking requests or requires a CAPTCHA.")
    except requests.exceptions.Timeout:
        print("Request to Amazon timed out. The server did not respond in time.")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error for Amazon page: {conn_err}. Check network or DNS.")
    except requests.exceptions.RequestException as e: # Catch other request-related errors
        print(f"Error fetching Amazon page: {e}")
    except Exception as e:
        import traceback # Import here to keep it local to this exceptional case
        print(f"An unexpected error occurred during scraping: {e}")
        traceback.print_exc() # Print full traceback for dev debugging

    return products_found

def search_amazon_products(product_title: str) -> list[dict]:
    """
    Public interface for searching products on Amazon.
    DEV/TEST ONLY: This uses web scraping for amazon.in based on user-confirmed permission.
    NOT FOR PRODUCTION. Production should use PAAPI or a similar official API.
    Rate limiting is handled by the scraping function.
    """
    print(f"Starting Amazon product search for: '{product_title}' (using DEV scraper).")
    if not product_title or not product_title.strip():
        print("Product title is empty. Skipping Amazon search.")
        return []

    scraped_products = _scrape_amazon_search_results_page(product_title)

    if not scraped_products:
        print(f"Scraping returned no results for '{product_title}'.")
        # Fallback to dummy data can be re-enabled here if needed for development flow.
        # For this subtask, if scraping fails, it returns empty.
        # e.g., return _get_dummy_products(product_title)
        pass # Explicitly doing nothing more if no products found

    return scraped_products

# def _get_dummy_products(product_title: str): # Example of dummy data function if needed
#     print(f"Returning DUMMY products for '{product_title}' as scraping failed or yielded no results.")
#     return [
#         {
#             "title": f"Dummy Amazon Product 1 for '{product_title}'",
#             "price": "₹1,999.00",
#             "image_url": "https://via.placeholder.com/150?text=Amazon+Dummy+1",
#             "product_url": "#product1_dummy_amazon_link"
#         },
#         {
#             "title": f"Dummy Amazon Product 2 for '{product_title}'",
#             "price": "₹2,499.00",
#             "image_url": "https://via.placeholder.com/150?text=Amazon+Dummy+2",
#             "product_url": "#product2_dummy_amazon_link"
#         }
#     ]

if __name__ == '__main__':
    # This block is for direct testing of this script.
    # Note: Running this directly will make actual network requests to Amazon.in.
    print("Starting direct test of amazon_api.py scraper...")

    # Test case 1: A common product
    # test_search_term = "iphone 15 pro max"
    # print(f"\n[Test Case 1: Searching for '{test_search_term}']")
    # products = search_amazon_products(test_search_term)
    # if products:
    #     print(f"Found {len(products)} products:")
    #     for p in products:
    #         print(f"  - Title: {p['title'][:50]}... | Price: {p['price']} | Image: {bool(p['image_url'])} | URL: {p['product_url'][:50]}...")
    # else:
    #     print("No products found.")

    # Test case 2: Empty search term
    # print("\n[Test Case 2: Empty search term]")
    # products_empty = search_amazon_products("")
    # if not products_empty:
    #     print("Correctly returned empty list for empty search term.")
    # else:
    #     print(f"Error: Expected empty list, got {len(products_empty)} products.")

    # Test case 3: Potentially problematic search term (e.g., very long, special chars)
    # test_search_term_problematic = "a" # "a" * 500 # very long
    # print(f"\n[Test Case 3: Problematic search term '{test_search_term_problematic}']")
    # products_problematic = search_amazon_products(test_search_term_problematic)
    # if products_problematic:
    #      print(f"Found {len(products_problematic)} products.")
    # else:
    #      print("No products found (or error occurred).")

    print("\nDirect test finished. Note: Actual scraping depends on Amazon's current page structure and anti-scraping measures.")
    # To see detailed scraping attempts, uncomment print statements within _scrape_amazon_search_results_page
    pass # Keep main guard clean for subtask submission as per original instructions.
