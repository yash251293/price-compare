import requests
from bs4 import BeautifulSoup

def extract_product_title(url: str) -> str | None:
    """
    Fetches a webpage and extracts the product title.

    Args:
        url: The URL of the product page.

    Returns:
        The product title if found, otherwise None.
    """
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try Open Graph meta tag
            og_title_tag = soup.find("meta", property="og:title")
            if og_title_tag and og_title_tag.get("content"):
                return og_title_tag["content"].strip()

            # Try page title tag
            if soup.title and soup.title.string:
                return soup.title.string.strip()

            return None
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}") # Optional: for logging or debugging
        return None

if __name__ == '__main__':
    # Example Usage (optional - for testing)
    test_url_amazon = "https://www.amazon.in/dp/B089MTR9A6" # Replace with a valid product URL
    test_url_flipkart = "https://www.flipkart.com/apple-iphone-15-blue-128-gb/p/itmbf140ce748952"

    title_amazon = extract_product_title(test_url_amazon)
    if title_amazon:
        print(f"Amazon Product Title: {title_amazon}")
    else:
        print("Could not extract title from Amazon.")

    title_flipkart = extract_product_title(test_url_flipkart)
    if title_flipkart:
        print(f"Flipkart Product Title: {title_flipkart}")
    else:
        print("Could not extract title from Flipkart.")

    # Example with a non-existent or problematic URL
    # test_url_invalid = "http://thisurldoesnotexist12345.com"
    # title_invalid = extract_product_title(test_url_invalid)
    # if title_invalid:
    #     print(f"Product Title: {title_invalid}")
    # else:
    #     print("Could not extract title (invalid URL).")

    # test_url_no_title = "https://www.example.com" # A site that might not have specific product title tags
    # title_no_specifics = extract_product_title(test_url_no_title)
    # if title_no_specifics:
    #     print(f"Page Title: {title_no_specifics}")
    # else:
    #     print("Could not extract title from example.com.")
