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
            return jsonify(error="Could not extract a valid product title from the provided link. Please check the URL and try again."), 400

        # For now, we are using the dummy search_amazon_products
        # In a real scenario, search_amazon_products itself might raise exceptions or return errors
        product_list = search_amazon_products(title)

        # search_amazon_products currently returns a list. If it could return None or error:
        # if product_list is None:
        #     return jsonify(error="Failed to retrieve products from the store API."), 500

        # If product_list is empty, it's not an error, just no results.
        # The frontend will handle the "No products found" message.
        return jsonify(products=product_list)

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Network error during title extraction: {e}")
        return jsonify(error=f"Network error while trying to access the product link: {e}. Please ensure the link is accessible."), 500
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"An unexpected error occurred during search: {e}")
        # Return a generic error message to the user
        return jsonify(error="An unexpected server error occurred. Please try again later."), 500

if __name__ == '__main__':
    app.run(debug=True)
