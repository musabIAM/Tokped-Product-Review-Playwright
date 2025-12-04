# Tokopedia Product and Review Dataset

## Overview
This dataset contains product and review data scraped from Tokopedia, a major Indonesian e-commerce platform. The data is structured to support product analysis, review mining, and e-commerce research.

## Files
- `product_data_with_reviews2.json`: Raw product data with embedded reviews (JSON format).
- `products_with_review_fields.csv`: Product data with review fields as lists (CSV format).
- `all_reviews_flat.csv`: (Optional) Flattened reviews, one row per review (CSV format).

## Columns
### Product Columns
- `product_id`: Unique identifier for the product
- `name`: Product name
- `category`: Product category
- `count_sold`: Number of units sold
- `discounted_price`: Discounted price (if any)
- `preorder`: Preorder status
- `price`: Original price
- `stock`: Stock available
- `gold_merchant`: Gold merchant status
- `is_official`: Official store status
- `is_topads`: TopAds (advertised) status
- `rating_average`: Average product rating
- `shop_id`: Shop identifier
- `shop_location`: Shop location
- `warehouse_id`: Warehouse identifier
- `url`: Product URL

### Review Columns (as lists per product)
- `review_id`: List of review IDs
- `variant_name`: List of variant names for each review
- `message`: List of review texts
- `review_rating`: List of review ratings
- `review_time`: List of review times (string)
- `review_timestamp`: List of review timestamps (int)
- `review_response`: List of seller responses
- `review_like`: List of like counts per review
- `bad_rating_reason`: List of reasons for bad ratings

## Usage
- Use the CSV or JSON files for data analysis in Python (pandas), R, or Excel.
- For review-level analysis, flatten the review columns so each row is a single review (see notebook for example code).

## Categories Included
This dataset covers the following Tokopedia product categories:

- Rumah Tangga (Household)
- Audio, Kamera & Elektronik Lainnya (Audio, Camera & Other Electronics)
- Buku (Books)
- Dapur (Kitchen)
- Elektronik (Electronics)
- Fashion Anak & Bayi (Kids & Baby Fashion)
- Fashion Muslim (Muslim Fashion)
- Fashion Pria (Men's Fashion)
- Fashion Wanita (Women's Fashion)
- Film & Musik (Film & Music)
- Gaming
- Handphone & Tablet (Phones & Tablets)
- Ibu & Bayi (Mother & Baby)
- Kecantikan (Beauty)
- Kesehatan (Health)
- Komputer & Laptop (Computers & Laptops)
- Logam Mulia (Precious Metals)
- Mainan & Hobi (Toys & Hobbies)
- Makanan & Minuman (Food & Beverages)
- Office & Stationery
- Olahraga (Sports)
- Otomotif (Automotive)
- Perawatan Hewan (Pet Care)
- Perawatan Tubuh (Body Care)

## License
This dataset is for research and educational purposes only. Please respect Tokopedia's terms of service and robots.txt.

## Acknowledgements
- Data collected using Playwright and Python
- Inspired by e-commerce data mining and NLP research
