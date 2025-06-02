import requests
from bs4 import BeautifulSoup
import logging
import traceback # Ensure traceback is imported

# Configure basic logging for the script.
# This module-level configuration will be used if no other configuration (e.g., from Flask app)
# takes precedence when this module is imported.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')

# List of User-Agents to try (can be expanded)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0'
]

# For identifying the problematic URL to save its content
TARGET_DEBUG_URL_PREFIX = "https://www.amazon.in/dp/B09V7GM5M8"

def extract_product_title(url: str) -> str | None:
    logging.info(f"Attempting to extract title from URL: {url}")
    if not url:
        logging.warning("Received empty URL for title extraction.")
        return None

    if not url.startswith(('http://', 'https://')):
        logging.warning(f"URL '{url}' does not have a scheme. Prepending 'https://'.")
        url = f"https://{url}"

    try:
        headers = {
            'User-Agent': USER_AGENTS[0], # Use the first User-Agent for now
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8', # Added Hindi
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.google.com/', # Added generic Referer
            'DNT': '1', # Do Not Track
            'Connection': 'keep-alive',
        }
        logging.info(f"Using headers: {headers}")

        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True) # Increased timeout from 10 to 15

        final_url = response.url # Get final URL after all redirects
        logging.info(f"Request to {url} resulted in final URL: {final_url}")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logging.info(f"Request successful. Status code: {response.status_code} for {final_url}")

        # Log response headers
        log_headers = "\n".join([f"{k}: {v}" for k,v in response.headers.items()])
        logging.info(f"Response Headers from server ({final_url}):\n{log_headers}")

        html_content = response.content

        # If this is the specific URL we are debugging, save its full HTML content
        if final_url.startswith(TARGET_DEBUG_URL_PREFIX):
            try:
                # Using a more specific filename based on the URL or a timestamp might be better
                # if multiple debugs are run, but for now, this is fine.
                filename_to_save = "temp_final_page_content.html"
                with open(filename_to_save, "wb") as f: # write bytes
                    f.write(html_content)
                logging.info(f"Saved full HTML content for {final_url} to '{filename_to_save}'")
            except Exception as e_file:
                logging.error(f"Error saving '{filename_to_save}': {e_file}")

        soup = BeautifulSoup(html_content, 'html.parser')

        head_tag = soup.find('head')
        if head_tag:
            head_snippet = head_tag.prettify(formatter="html")[:300]
            logging.info(f"HTML <head> snippet (first 300 chars of prettified head for {final_url}):\n{head_snippet}")
        else:
            logging.info(f"HTML <head> tag not found for {final_url}.")
            body_tag = soup.find('body')
            if body_tag:
                 body_snippet = body_tag.prettify(formatter="html")[:300]
                 logging.info(f"HTML <body> snippet (first 300 chars for {final_url}):\n{body_snippet}")
            else:
                 raw_snippet = html_content.decode('utf-8', errors='ignore')[:300]
                 logging.info(f"Raw HTML snippet (first 300 chars for {final_url}):\n{raw_snippet}")

        # Try to get Open Graph title
        og_title_tag = soup.find("meta", property="og:title")
        if og_title_tag and og_title_tag.get("content"):
            title = og_title_tag["content"].strip()
            if title:
                logging.info(f"Found Open Graph (og:title) for {final_url}: '{title}'")
                return title
            else:
                logging.info(f"Open Graph (og:title) found for {final_url} but was empty after stripping.")
        else:
            logging.info(f"Open Graph (og:title) tag not found or has no content attribute for {final_url}.")

        # If no OG title, try to get the HTML title tag
        html_title_tag = soup.title
        if html_title_tag and html_title_tag.string:
            title = html_title_tag.string.strip()
            if title:
                logging.info(f"Found HTML <title> tag for {final_url}: '{title}'")
                return title
            else:
                logging.info(f"HTML <title> tag found for {final_url} but was empty after stripping.")
        else:
            logging.info(f"HTML <title> tag not found or has no string content for {final_url}.")

        # Fallback: Try to find a prominent h1 tag if others fail
        # Specifically look for Amazon's #productTitle first
        h1_product_title_element = soup.select_one('h1#productTitle')
        if h1_product_title_element:
             title = h1_product_title_element.get_text(strip=True)
             if title:
                 logging.info(f"Found H1#productTitle for {final_url}: '{title}'")
                 return title
             else:
                 logging.info(f"H1#productTitle found for {final_url} but was empty after stripping.")
        else:
            logging.info(f"H1#productTitle not found for {final_url}.")
            # Generic H1 as a further fallback
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text(strip=True)
                if title:
                    logging.info(f"Found generic H1 tag content as fallback for {final_url}: '{title}'")
                    return title
                else:
                    logging.info(f"Generic H1 tag found for {final_url} but was empty after stripping.")
            else:
                logging.info(f"No generic H1 tag found for fallback title for {final_url}.")

        logging.warning(f"Could not extract a usable title for URL: {final_url}")
        return None

    except requests.exceptions.HTTPError as http_err:
        # Ensure response object is available before trying to access its attributes
        status_code_info = http_err.response.status_code if http_err.response else "Unknown Status"
        final_url_info = http_err.response.url if http_err.response else "Unknown URL"
        logging.error(f"HTTP error for {url} (final URL: {final_url_info}): {http_err} - Status code: {status_code_info}")
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while fetching {url} (timeout set to 15s)")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred while fetching {url}: {conn_err}. Check network or URL.")
    except requests.exceptions.RequestException as e: # Catch other request-related errors
        logging.error(f"A generic requests error occurred while fetching {url}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during title extraction for {url}: {e}")
        logging.error(traceback.format_exc())

    return None

if __name__ == '__main__':
    # This section is for direct testing of this script.
    # Examples of how to use it (uncomment to run):

    # # Re-configure logging for direct script run if necessary to see all levels
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s', force=True)
    # logging.info("Starting a direct test of extract_product_title...")

    # # Test with a known good, direct product URL
    # test_url_direct_product = "https://www.amazon.in/dp/B09V7GM5M8"
    # logging.info(f"Testing with direct product URL: {test_url_direct_product}")
    # title_direct = extract_product_title(test_url_direct_product)
    # if title_direct:
    #     logging.info(f"Test with URL '{test_url_direct_product}' SUCCEEDED. Title: '{title_direct}'")
    # else:
    #     logging.error(f"Test with URL '{test_url_direct_product}' FAILED to extract title.")

    # # Test with a known short URL that redirects
    # test_short_url_known = "https://amzn.in/d/4UrxwQU" # This resolved to B09V7GM5M8 in tests
    # logging.info(f"Testing with short URL: {test_short_url_known}")
    # title_short_known = extract_product_title(test_short_url_known)
    # if title_short_known:
    #      logging.info(f"Test with short URL '{test_short_url_known}' SUCCEEDED. Title: '{title_short_known}'")
    # else:
    #      logging.error(f"Test with short URL '{test_short_url_known}' FAILED.")

    # # Test with a URL that might require scheme prepending
    # test_url_no_scheme = "www.flipkart.com/philips-mg3710-65-runtime-60-min-trimmer-men/p/itm15f671a69e104"
    # logging.info(f"Testing with URL missing scheme: {test_url_no_scheme}")
    # title_no_scheme = extract_product_title(test_url_no_scheme)
    # if title_no_scheme:
    #      logging.info(f"Test with URL '{test_url_no_scheme}' (after prepending scheme) SUCCEEDED. Title: '{title_no_scheme}'")
    # else:
    #      logging.error(f"Test with URL '{test_url_no_scheme}' FAILED.")

    pass
