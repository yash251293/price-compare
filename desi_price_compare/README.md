# Desi Price Comparison Web App

This application allows users to paste a product link from certain e-commerce sites, extracts the product title, and then searches for matching products on Amazon.in to compare prices.

## ⚠️ Important Warning: Amazon.in Integration (Development/Testing Only)

The current integration for fetching product data from **Amazon.in** uses a **web scraper**. This implementation is strictly for **DEVELOPMENT AND TESTING PURPOSES ONLY**.

*   **Basis of Use:** This scraper has been implemented based on explicit, user-confirmed permission from Amazon, applicable **only for development and testing phases** for this specific project.
*   **Rate Limiting:** The scraper is rate-limited to approximately **10 requests per minute** to `amazon.in` to comply with the development/testing permission conditions.
*   **Fragility:** Web scrapers are inherently fragile and can break if Amazon.in changes its website HTML structure. The selectors used may require updates over time.
*   **DO NOT USE IN PRODUCTION:** This scraper **MUST NOT BE USED IN A PRODUCTION ENVIRONMENT.** Deploying this scraper to a live, user-facing application would likely violate Amazon's general Terms of Service and could lead to IP blocks or other actions from Amazon.

### Production Environment Requirements

For a production environment, this application **must be updated to use the official Amazon Product Advertising API (PAAPI)** for accessing Amazon product data. Using the PAAPI ensures compliance with Amazon's terms and provides a more stable and reliable integration.

**Future Configuration (Recommended):**

It is recommended to implement an environment variable (e.g., `APP_ENV`) to switch between data sources:

*   `APP_ENV=development`: Use the current web scraper for `amazon.in` (with all the above warnings).
*   `APP_ENV=production`: Use a (to-be-implemented) PAAPI client.

## Current Features

*   Parses product links to extract product titles.
*   Searches for products on Amazon.in using the extracted title (via dev-only scraper).
*   Displays matching Amazon.in products with name, price, image, and a link to the product page.

## Setup and Running (from within the `desi_price_compare` directory)

1.  **Clone the repository (or ensure you are in the `desi_price_compare` project directory).**
    ```bash
    # git clone https://your_repo_url/desi_price_compare.git
    # cd desi_price_compare
    ```
    (Replace `https://your_repo_url/desi_price_compare.git` with the actual repository URL if applicable)

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the Flask development server:**
    *   Set the Flask application (if not already set or if running from outside the project's root `desi_price_compare` directory):
        ```bash
        export FLASK_APP=app.py  # On Linux/macOS
        # set FLASK_APP=app.py    # On Windows (in Command Prompt)
        # $env:FLASK_APP="app.py" # On Windows (in PowerShell)
        ```
    *   Run the app:
        ```bash
        flask run
        ```
    *   The application will typically be available at `http://127.0.0.1:5000/`.

## Running Tests (from within the `desi_price_compare` directory)

To run the unit tests:
```bash
pytest
```

This will discover and run tests located in the `tests/` directory.
