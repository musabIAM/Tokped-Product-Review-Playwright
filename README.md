# Tokopedia Product and Review Dataset

## Overview
This dataset contains product and review data scraped from Tokopedia, a major Indonesian e-commerce platform. The data is structured to support product analysis, review mining, and e-commerce research. The scraper is built with a modular, testable architecture using Python, Playwright, and modern software engineering practices.

## Datasets
Datasest available at kaggle https://www.kaggle.com/datasets/musabiam/tokopedia-product-and-review-dataset

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

## Architecture

### Core Components

**scraper.py** - Data models and services:
- `Product` dataclass: 17 fields including product_id, category, pricing, ratings, shop info, reviews
- `ScraperConfig` dataclass: 13 configuration parameters (headless, batch_size, max_workers, scroll_steps, retry settings, pool settings)
- `ReviewFetcher` class: Fetches reviews via GraphQL with pagination, supports parallel batch processing via ThreadPoolExecutor
- `ProductExtractor` class: Extracts products from Playwright-intercepted JSON responses
- Helper functions: `normalize_price()`, `normalize_category()`, `batcher()`, `make_session()`

**main.py** - Orchestration layer:
- `TokopediaScrapeJob` class: Class-based job management with configurable workflows
- `scrape_products()`: Playwright automation with network interception and scrolling
- `fetch_and_attach_reviews()`: Batch parallel review fetching with ThreadPoolExecutor
- `load_products_from_json()`: Load existing products for independent review fetching
- `run(include_reviews=True)`: Unified entry point for full or partial workflows

### Key Features

- **Modular Architecture**: Dataclasses for type safety, dependency injection for testability
- **Robust HTTP Layer**: urllib3.Retry with exponential backoff (5 retries, status_forcelist=[429,500,502,503,504])
- **Connection Pooling**: HTTPAdapter with configurable pool_connections (50) and pool_maxsize (50)
- **Batch Processing**: Configurable batch_size with parallel fetching via ThreadPoolExecutor
- **Network Interception**: Playwright intercepts JSON responses for efficient product extraction
- **Comprehensive Testing**: 28 unit tests with mocked HTTP responses (no live network calls)

### Configuration

```python
from scraper import ScraperConfig, TokopediaScrapeJob

cfg = ScraperConfig(
    headless=False,
    batch_size=25,
    max_workers=8,
    scroll_steps=5,
    retry_total=5,
    backoff_factor=0.5
)

job = TokopediaScrapeJob(
    paths=["buku", "elektronik"],
    cfg=cfg,
    output_path="products.json",
    review_output_path="reviews.json"
)

job.run(include_reviews=True)
```

## Usage

### Running the Scraper

```bash
# Install dependencies
pip install playwright requests urllib3 pandas

# Install Playwright browser (required once)
playwright install

# Run scraper
python -c "
from main import TokopediaScrapeJob
from scraper import ScraperConfig

cfg = ScraperConfig(scroll_steps=10, headless=False)
job = TokopediaScrapeJob(paths=['buku'], cfg=cfg)
job.run(include_reviews=True)
"
```

### Running Tests

```bash
# Run all tests
python -m unittest discover -s . -p "test_*.py"

# Run specific test module
python -m unittest test_scraper
python -m unittest test_main

# Run with coverage
python -m pytest test_scraper.py --cov=scraper --cov-report=html
```

### Data Analysis

Use the Jupyter notebook `ip.ipynb` for:
- Loading product and review data from JSON
- Flattening reviews (one row per review)
- Column renaming (url→product_url, like_dislike→review_like, rating→review_rating)
- CSV export for analysis

```python
# Example: Load and flatten reviews
import pandas as pd

df = pd.read_json('product_data_with_reviews2.json')
reviews = df.explode('reviews')
```

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

## Testing

The project includes 28 comprehensive unit tests:

**test_scraper.py** (17 tests):
- TestDataModels: Product and ScraperConfig dataclass instantiation
- TestHelpers: normalize_price, normalize_category, batcher, make_session
- TestProductExtractor: Extraction from valid/empty/None JSON inputs
- TestReviewFetcher: Single-page, multi-page pagination, parallel fetching
- TestProductsToDict: Dataclass to dict conversion

**test_main.py** (11 tests):
- TestSaveProductDataJson: JSON saving functionality
- TestTokopediaScrapeJob: Initialization, configuration overrides, JSON loading, review fetching, response handling

All tests use `unittest.mock` to avoid live network calls and verify behavior in isolation.

## Dependencies

```
playwright>=1.40.0
requests>=2.31.0
urllib3>=2.0.0
pandas>=2.0.0
```

## Error Handling & Retries

- **HTTP Retries**: Exponential backoff with urllib3.Retry (5 retries, backoff_factor=0.5)
- **Status-based Retries**: Automatic retry on 429 (rate limit), 500, 502, 503, 504
- **Connection Pooling**: 50 connections per host to prevent SSL/connection errors
- **Batch Processing**: Configurable delays between batches to respect server load
- **Logging**: INFO-level logging for batch progress, review pagination, HTTP status codes

## Performance

- **Parallel Review Fetching**: ThreadPoolExecutor with configurable max_workers (default 8)
- **Batch Processing**: Configurable batch_size (default 25) for memory efficiency
- **Connection Reuse**: HTTPAdapter maintains persistent connections within pool
- **Network Interception**: Playwright intercepts JSON responses, avoiding DOM parsing overhead

## Production Considerations

- Use `headless=True` for server deployments
- Adjust `scroll_steps`, `batch_size`, and `max_workers` based on:
  - Target dataset size (scroll_steps: more steps = more products)
  - Memory constraints (batch_size: smaller batches = less memory)
  - Server capacity (max_workers: more workers = higher throughput but more load)
- Monitor logging output for rate limiting (429 responses) and adjust delays
- Use separate `scrape_products()` and `fetch_and_attach_reviews()` calls for large datasets to enable resumable workflows

## License

This dataset and scraper are for research and educational purposes only. Please respect Tokopedia's terms of service and robots.txt.

**Recommended License**: CC BY-NC 4.0 (Creative Commons Attribution-NonCommercial)

## Acknowledgements

- Built with [Playwright](https://playwright.dev/) for robust browser automation
- [requests](https://requests.readthedocs.io/) + [urllib3](https://urllib3.readthedocs.io/) for reliable HTTP with exponential backoff
- [Pandas](https://pandas.pydata.org/) for data analysis and transformation
- Inspired by e-commerce data mining and NLP research

