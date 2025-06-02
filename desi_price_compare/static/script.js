// This script will be triggered after the form submission and API response.

function displayProducts(products) {
    const container = document.getElementById('search-results-container');
    if (!container) {
        console.error('Search results container not found!');
        return;
    }

    container.innerHTML = ''; // Clear previous results

    if (!products || products.length === 0) {
        container.innerHTML = '<p style="color: #555;">No products found for your query.</p>'; // Clearer message
        return;
    }

    const ul = document.createElement('ul');
    ul.style.listStyleType = 'none'; // Basic styling
    ul.style.padding = '0';

    products.forEach(product => {
        const li = document.createElement('li');
        li.style.border = '1px solid #ddd'; // Basic card styling
        li.style.marginBottom = '10px';
        li.style.padding = '10px';
        li.style.display = 'flex'; // Use flexbox for better alignment
        li.style.alignItems = 'center';


        // Product Image
        const img = document.createElement('img');
        img.src = product.image_url;
        img.alt = product.title;
        img.style.width = '100px'; // Fixed width
        img.style.height = '100px'; // Fixed height
        img.style.objectFit = 'contain'; // Ensure image fits well
        img.style.marginRight = '15px';
        li.appendChild(img);

        const productDetailsDiv = document.createElement('div');

        // Product Title and Link
        const titleLink = document.createElement('a');
        titleLink.href = product.product_url;
        titleLink.textContent = product.title;
        titleLink.target = '_blank'; // Open in new tab
        titleLink.style.textDecoration = 'none';
        titleLink.style.color = '#0066cc';

        const titleHeader = document.createElement('h4'); // Slightly smaller header
        titleHeader.style.margin = '0 0 5px 0';
        titleHeader.appendChild(titleLink);
        productDetailsDiv.appendChild(titleHeader);

        // Product Price
        const pricePara = document.createElement('p');
        pricePara.textContent = `${product.price}`; // Removed "Price: " prefix for cleaner look
        pricePara.style.color = 'green';
        pricePara.style.margin = '0 0 10px 0';
        productDetailsDiv.appendChild(pricePara);

        // Buy Button (More prominent)
        const buyButton = document.createElement('a');
        buyButton.href = product.product_url;
        buyButton.textContent = 'View on Store';
        buyButton.target = '_blank';
        buyButton.style.display = 'inline-block';
        buyButton.style.padding = '8px 12px';
        buyButton.style.backgroundColor = '#007bff';
        buyButton.style.color = 'white';
        buyButton.style.textDecoration = 'none';
        buyButton.style.borderRadius = '4px';
        productDetailsDiv.appendChild(buyButton);

        li.appendChild(productDetailsDiv);
        ul.appendChild(li);
    });

    container.appendChild(ul);
}


document.addEventListener('DOMContentLoaded', () => {
    const productLinkForm = document.getElementById('product-link-form');
    const resultsContainer = document.getElementById('search-results-container');

    if (productLinkForm) {
        productLinkForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent default form submission

            const productLinkInput = productLinkForm.querySelector('input[name="product_link"]');
            const productLink = productLinkInput ? productLinkInput.value.trim() : "";

            if (productLink === "") {
                resultsContainer.innerHTML = '<p style="color: red;">Please paste a product link.</p>';
                productLinkInput.focus(); // Focus on the input field
                return;
            }

            // Show a loading message
            resultsContainer.innerHTML = '<p style="color: #333;"><em>Searching for products... Please wait.</em></p>';

            try {
                const formData = new FormData();
                formData.append('product_link', productLink);

                const response = await fetch('/search', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    if (data.products) {
                        displayProducts(data.products); // This function handles empty products array
                    } else if (data.error) { // Backend error explicitly sent
                        resultsContainer.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${data.error}</p>`;
                    } else { // Unexpected response structure from backend
                        resultsContainer.innerHTML = '<p style="color: red;">Received an unexpected response from the server.</p>';
                    }
                } else { // HTTP error status (4xx, 5xx)
                    if (data.error) {
                        resultsContainer.innerHTML = `<p style="color: red;"><strong>Error ${response.status}:</strong> ${data.error}</p>`;
                    } else {
                        resultsContainer.innerHTML = `<p style="color: red;">An error occurred on the server (Status: ${response.status}). Please try again.</p>`;
                    }
                }

            } catch (error) {
                console.error('Fetch error:', error);
                resultsContainer.innerHTML = `<p style="color: red;">Failed to connect to the server. Please check your internet connection or try again later. (${error.message})</p>`;
            }
        });
    }
});

// Example usage (for testing displayProducts - can be removed later):
// document.addEventListener('DOMContentLoaded', () => {
//     const dummyProducts = [
//         {
//             "title": "Dummy Product 1 for 'Test'",
//             "price": "₹999.00",
//             "image_url": "https://via.placeholder.com/150?text=Product+1",
//             "product_url": "#product1_dummy_link"
//         },
//         {
//             "title": "Dummy Product 2 for 'Test'",
//             "price": "₹1,499.00",
//             "image_url": "https://via.placeholder.com/150?text=Product+2",
//             "product_url": "#product2_dummy_link"
//         }
//     ];
//     // To test, uncomment the line below and open index.html in a browser
//     // displayProducts(dummyProducts);
//     // To test empty state:
//     // displayProducts([]);
// });
