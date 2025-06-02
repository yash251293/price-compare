import requests
from bs4 import BeautifulSoup
import logging # Use logging module
import traceback # Import traceback for logging stack traces

# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

def extract_product_title(url: str) -> str | None:
    logging.info(f"Attempting to extract title from URL: {url}")
    if not url:
        logging.warning("Received empty URL.")
        return None

    if not url.startswith(('http://', 'https://')):
        logging.warning(f"URL '{url}' does not have a scheme. Prepending 'https://'.")
        url = f"https://{url}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8', # Added en-IN
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'DNT': '1', # Do Not Track
            'Connection': 'keep-alive'
        }
        # Allow redirects is True by default. timeout can be important.
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True) # Increased timeout

        # Log final URL after potential redirects
        logging.info(f"Request to {url} resulted in final URL: {response.url}")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        logging.info(f"Request successful. Status code: {response.status_code} for {response.url}")

        html_content = response.content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Log a snippet of the head content for debugging
        head_tag = soup.find('head')
        if head_tag:
            # Using .decode on content and then slicing to avoid issues with partial unicode chars
            head_snippet = head_tag.prettify(formatter="html")[:300] # Get first 300 chars of prettified head
            logging.info(f"HTML <head> snippet (first 300 chars of prettified head):\n{head_snippet}")
        else:
            logging.info("HTML <head> tag not found.")
            # Log beginning of body or raw HTML if head is missing
            body_tag = soup.find('body')
            if body_tag:
                 body_snippet = body_tag.prettify(formatter="html")[:300]
                 logging.info(f"HTML <body> snippet (first 300 chars of prettified body):\n{body_snippet}")
            else:
                 # Attempt to decode for logging, ignore errors for robustness
                 raw_snippet = html_content.decode('utf-8', errors='ignore')[:300]
                 logging.info(f"Raw HTML snippet (first 300 chars, decoded with error ignore):\n{raw_snippet}")

        # Try to get Open Graph title
        og_title_tag = soup.find("meta", property="og:title")
        if og_title_tag and og_title_tag.get("content"):
            title = og_title_tag["content"].strip()
            logging.info(f"Found Open Graph (og:title) for {response.url}: '{title}'")
            return title

        logging.info(f"Open Graph (og:title) not found or empty for {response.url}.")

        # If no OG title, try to get the HTML title tag
        html_title_tag = soup.title
        if html_title_tag and html_title_tag.string:
            title = html_title_tag.string.strip()
            logging.info(f"Found HTML <title> tag for {response.url}: '{title}'")
            return title

        logging.warning(f"HTML <title> tag not found or empty for {response.url}.")
        return None

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error for {url} (final URL: {http_err.response.url if http_err.response else 'N/A'}): {http_err} - Status code: {http_err.response.status_code if http_err.response else 'N/A'}")
    except requests.exceptions.Timeout:
        logging.error(f"Timeout occurred while fetching {url}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"Connection error occurred while fetching {url}: {conn_err}. Check network or URL.")
    except requests.exceptions.RequestException as e: # Catch other request-related errors
        logging.error(f"A requests error occurred while fetching {url}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during parsing or other operations
        logging.error(f"An unexpected error occurred during title extraction for {url}: {e}")
        logging.error(traceback.format_exc()) # Log the full stack trace

    return None

if __name__ == '__main__':
    # This section is for direct testing of this script.
    # Examples of how to use it:

    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s : %(message)s', force=True)
    # logging.info("Starting a direct test of extract_product_title...")

    # test_url = "https://www.amazon.in/dp/B09G92334S" # Example product
    # logging.info(f"Testing with URL: {test_url}")
    # title = extract_product_title(test_url)
    # if title:
    #     logging.info(f"Test with URL '{test_url}' SUCCEEDED. Title: '{title}'")
    # else:
    #     logging.error(f"Test with URL '{test_url}' FAILED to extract title.")

    # test_short_url = "https://amzn.in/d/1acVKXm"
    # logging.info(f"Testing with short URL: {test_short_url}")
    # title_short = extract_product_title(test_short_url)
    # if title_short:
    #      logging.info(f"Test with short URL '{test_short_url}' SUCCEEDED. Title: '{title_short}'")
    # else:
    #      logging.error(f"Test with short URL '{test_short_url}' FAILED.")
    pass
