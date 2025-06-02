import time
import requests
from bs4 import BeautifulSoup
import logging
import traceback # Ensure traceback is imported
from urllib.parse import quote # For URL encoding

# Configure basic logging for the script.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')

# List of User-Agents to try (can be expanded)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0'
]

REQUEST_INTERVAL = 6
TARGET_DEBUG_URL_PREFIX = "https://www.amazon.in/dp/B09V7GM5M8" # For link_parser debugging, not directly used in scraper

def _simplify_search_query(title: str, max_words: int = 6) -> str:
    if not title:
        return ""

    # Remove common trailing parts like ": Amazon.in: Health & Personal Care"
    # Split by known major delimiters first
    simplified_title = title.split('|')[0].strip()
    simplified_title = simplified_title.split(':')[0].strip() # Take part before first colon

    # Further remove "Amazon.in" if it's part of the core string now
    simplified_title = simplified_title.replace("Amazon.in", "").strip()

    words = simplified_title.split()

    if len(words) > max_words:
        query_words = words[:max_words]
    elif len(words) > 2 and len(words) <= max_words: # if it's 3-max_words words, use as is
        query_words = words
    elif words: # if 1-2 words, use as is
        query_words = words
    else: # Should not happen if title was not empty
        return ""

    return " ".join(query_words).strip()


def _scrape_amazon_search_results_page(product_title: str) -> list[dict]:
    """
    Scrapes Amazon.in search results for a given product title.
    DEV/TEST ONLY for amazon.in. NOT FOR PRODUCTION.
    User-confirmed permission for dev/test scraping in this specific context.
    Rate limit: Attempts to respect ~10 requests per minute via REQUEST_INTERVAL.
    """
    logging.info(f"Waiting for {REQUEST_INTERVAL} seconds due to rate limiting...")
    time.sleep(REQUEST_INTERVAL)

    original_title_for_search = product_title
    simplified_search_query = _simplify_search_query(original_title_for_search)

    if not simplified_search_query:
        logging.warning("Simplified search query is empty for original title: '{original_title_for_search}'. Aborting search.")
        return []

    logging.info(f"Original title for Amazon search: '{original_title_for_search}'")
    logging.info(f"Simplified search query for Amazon: '{simplified_search_query}'")

    search_url = f"https://www.amazon.in/s?k={quote(simplified_search_query)}"
    logging.info(f"Scraping Amazon.in using URL: {search_url}")

    headers = {
        'User-Agent': USER_AGENTS[0],
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.amazon.in/',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    products_found = []
    response = None
    try:
        response = requests.get(search_url, headers=headers, timeout=15)

        final_url_after_search_redirect = response.url # Get final URL, if search itself redirects
        logging.info(f"Search request to {search_url} resulted in final URL: {final_url_after_search_redirect}")
        response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
        logging.info(f"Search request successful. Status code: {response.status_code} for {final_url_after_search_redirect}")

        html_content = response.content # Store content after successful status check

        # Save the content of the search results page for debugging
        try:
            search_page_filename = "temp_amazon_search_results.html"
            with open(search_page_filename, "wb") as f: # write bytes
                f.write(html_content)
            logging.info(f"Saved search results HTML to '{search_page_filename}' for query: '{simplified_search_query}'")
        except Exception as e_file:
            logging.error(f"Error saving '{search_page_filename}': {e_file}")

        # Check for CAPTCHA or block page more robustly after saving content
        decoded_content_for_check = html_content.decode('utf-8', errors='ignore').lower()
        if "captcha" in decoded_content_for_check or "api-services-support@amazon.com" in decoded_content_for_check:
            logging.warning(f"CAPTCHA or block page detected on search results page for query '{simplified_search_query}'. Cannot scrape.")
            # HTML is already saved, so it can be inspected.
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        search_results_items = soup.find_all('div', {'data-component-type': 's-search-result'})
        if not search_results_items:
            logging.info("Primary selector 'div[data-component-type=\"s-search-result\"]' failed. Trying fallback...")
            search_results_items = soup.find_all('div', {'data-asin': True, 'class': lambda x: x and 's-result-item' in x.split()})

        if not search_results_items:
            logging.info(f"No search result items found using known selectors for query: '{simplified_search_query}'. Page structure might have changed.")
            # Consider saving this HTML for debugging search page structure if needed
            # with open(f"temp_search_page_{simplified_search_query[:20]}.html", "wb") as f:
            #     f.write(response.content)
            # logging.info(f"Saved search page HTML for query '{simplified_search_query}' for debugging.")
            return []

        for item_count, item in enumerate(search_results_items):
            title, price, image_url, product_url = None, None, None, None

            title_element = item.select_one('h2 a.a-link-normal span.a-text-normal')
            if title_element:
                title = title_element.get_text(strip=True)

            price_element = item.select_one('span.a-price > span.a-offscreen')
            if not price_element:
                price_element = item.select_one('span.a-price-whole')

            if price_element:
                price_str = price_element.get_text(strip=True)
                price_symbol_element = item.select_one('span.a-price-symbol')
                currency_symbol = ""
                if price_symbol_element:
                    currency_symbol = price_symbol_element.get_text(strip=True)

                # If price_str is just the symbol, get the whole part
                if price_str == currency_symbol and item.select_one('span.a-price-whole'):
                    price = currency_symbol + item.select_one('span.a-price-whole').get_text(strip=True)
                elif currency_symbol and currency_symbol not in price_str: # Prepend if symbol is missing
                    price = currency_symbol + price_str
                else:
                    price = price_str


            image_element = item.select_one('img.s-image')
            if image_element:
                image_url = image_element.get('src')

            url_element = item.select_one('h2 a.a-link-normal.s-underline-text')
            if not url_element: # Try another common link pattern for product title
                url_element = item.select_one('h2 a.a-link-normal, a.a-link-normal.s-no-outline') # Broader selector for h2 links
            if url_element: # Check if an element was found
                raw_url = url_element.get('href')
                if raw_url:
                    if not raw_url.startswith('https://www.amazon.in') and raw_url.startswith('/'):
                        product_url = f"https://www.amazon.in{raw_url}"
                    elif raw_url.startswith('https://www.amazon.in'):
                        product_url = raw_url

            if title and price and image_url and product_url: # Ensure all parts are found
                products_found.append({
                    "title": title,
                    "price": price,
                    "image_url": image_url,
                    "product_url": product_url
                })

            if len(products_found) >= 5:
                logging.info("Reached limit of 5 products for query.")
                break

        if not products_found:
            logging.info(f"No products extracted matching all criteria for query: '{simplified_search_query}'. Selectors might need an update or page content differs.")
        else:
            logging.info(f"Found {len(products_found)} products from scraping for query: '{simplified_search_query}'.")

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if hasattr(http_err, 'response') and http_err.response else 'Unknown Status'
        response_text_snippet = http_err.response.text[:500].lower() if hasattr(http_err, 'response') and http_err.response and hasattr(http_err.response, 'text') else '' # Increased snippet size
        logging.error(f"HTTP error occurred for query '{simplified_search_query}': {http_err} - Status: {status_code}")
        if status_code == 404:
            logging.error("Page not found for search query. Check search URL generation.")
        elif status_code == 503 or 'captcha' in response_text_snippet or 'api-services-support@amazon.com' in response_text_snippet:
            logging.error("Amazon might be temporarily blocking requests or requires a CAPTCHA for query.")
            # Save error page HTML if response object is available
            if hasattr(http_err, 'response') and http_err.response and hasattr(http_err.response, 'content'):
                 try:
                    # Sanitize filename from query
                    safe_query_filename_part = "".join([c if c.isalnum() else "_" for c in simplified_search_query])[:50]
                    error_page_filename = f"temp_amazon_error_page_{status_code}_{safe_query_filename_part}.html"
                    with open(error_page_filename, "wb") as f:
                        f.write(http_err.response.content)
                    logging.info(f"Saved error page HTML to '{error_page_filename}'")
                 except Exception as e_file_err:
                    logging.error(f"Error saving error page HTML: {e_file_err}")
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while fetching Amazon search page for query: '{simplified_search_query}'.")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred while fetching Amazon page for query '{simplified_search_query}': {conn_err}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Generic error fetching Amazon page for query '{simplified_search_query}': {e}")
    except Exception as e:
        # logging.error(f"An unexpected error occurred during scraping for query '{simplified_search_query}': {e}")
        # logging.error(traceback.format_exc()) # Already imported at top level
        logging.error(f"An unexpected error occurred during scraping for query '{simplified_search_query}': {e}\n{traceback.format_exc()}")

    return products_found

def search_amazon_products(product_title: str) -> list[dict]:
    """
    Public interface for searching products on Amazon.
    DEV/TEST ONLY: This uses web scraping for amazon.in based on user-confirmed permission.
    NOT FOR PRODUCTION. Production should use PAAPI or a similar official API.
    Rate limiting is handled by the scraping function.
    """
    logging.info(f"search_amazon_products called with title: '{product_title}' (scraper will simplify).")
    if not product_title or not product_title.strip():
        logging.warning("Product title is empty. Skipping Amazon search.")
        return []

    scraped_products = _scrape_amazon_search_results_page(product_title)

    if not scraped_products:
        logging.info(f"Scraping returned no results for original title: '{product_title}'.")
        # Fallback to dummy data can be re-enabled here if needed for development flow.
        # e.g., return _get_dummy_products(product_title)
        pass

    return scraped_products

if __name__ == '__main__':
    # This section is for direct testing of this script.
    # Examples of how to use it:

    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s', force=True)
    # logging.info("Starting a direct test of search_amazon_products with query simplification...")

    # test_title_long = "Philips India's No.1 Men's Trimmer | Self Sharpening Blades | Single Stroke Grooming I 9 in1 Face, Nose and Body I 2+1* year warranty | Powerful motor | No Oil Needed I 60 min runtime I MG3710/65 : Amazon.in: Health & Personal Care"
    # logging.info(f"Testing with long title: '{test_title_long}'")
    # products = search_amazon_products(test_title_long)
    # if products:
    #      logging.info(f"Test with long title SUCCEEDED. Found {len(products)} products.")
    #      # for p in products: logging.info(p)
    # else:
    #      logging.error(f"Test with long title FAILED to find products.")

    # test_title_short = "iPhone 15 Pro Max"
    # logging.info(f"Testing with short title: '{test_title_short}'")
    # products_short = search_amazon_products(test_title_short)
    # if products_short:
    #      logging.info(f"Test with short title SUCCEEDED. Found {len(products_short)} products.")
    # else:
    #      logging.error(f"Test with short title FAILED.")
    pass
