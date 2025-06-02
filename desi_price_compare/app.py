from flask import Flask, render_template, request, jsonify
from .link_parser import extract_product_title
from .amazon_api import search_amazon_products

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        product_link = request.form.get('product_link')
        if not product_link or not product_link.strip():
            return jsonify(error="Product link is missing or empty. Please provide a valid link."), 400

        title = extract_product_title(product_link)

        if not title or not title.strip():
            app.logger.warn(f"Title extraction failed for link: {product_link}")
            return jsonify(error="Could not extract a valid product title from the provided link. Please check the URL and try again."), 400

        app.logger.info(f"Successfully extracted title: '{title}' from link: {product_link}")

        # --- DEV/TEST ONLY ---
        # The current implementation of search_amazon_products uses a web scraper
        # for amazon.in, based on specific user-confirmed permission for dev/test.
        # This MUST be replaced by the official Amazon Product Advertising API (PAAPI)
        # or disabled for a production environment.
        # Future: Use an env var like APP_ENV to switch implementations.
        # --- END DEV/TEST ONLY ---
        try:
            # This now calls the scraper-enabled version from amazon_api.py
            product_list = search_amazon_products(title)

            if not product_list:
                 app.logger.info(f"Scraper returned no products for title: '{title}'. Link: {product_link}")
            else:
                 app.logger.info(f"Scraper found {len(product_list)} products for title: '{title}'.")

            # If product_list is empty, it's not an error, just no results.
            # The frontend handles the "No products found" message.
            return jsonify(products=product_list)

        except Exception as e:
            # This will catch errors from within search_amazon_products (e.g., scraper issues not caught internally)
            # or any other unexpected error in this block.
            app.logger.error(f"Error during Amazon product search for title '{title}': {e}", exc_info=True)
            return jsonify(error="An unexpected error occurred while searching for products on Amazon."), 500

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Network error during title extraction for link {product_link}: {e}", exc_info=True)
        return jsonify(error=f"Network error while trying to access the product link: '{e}'. Please ensure the link is accessible."), 500
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"An unexpected error occurred in /search route for link {product_link}: {e}", exc_info=True)
        # Return a generic error message to the user
        return jsonify(error="An unexpected server error occurred. Please try again later."), 500

if __name__ == '__main__':
    app.run(debug=True)
