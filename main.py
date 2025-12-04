from playwright.sync_api import sync_playwright
import time
import logging
import json
import requests
from pathlib import Path
from typing import List, Optional

from scraper import ScraperConfig, Product, ProductExtractor, ReviewFetcher, make_session, batcher, products_to_dict


class TokopediaScrapeJob:
    def __init__(
        self,
        paths: List[str] = [],
        cfg: Optional[ScraperConfig] = None,
        output_path: str = 'product_data.json',
        review_output_path: str = 'product_data_with_reviews.json',
        scroll_steps: Optional[int] = None,
        headless: Optional[bool] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.paths = paths
        self.cfg = cfg or ScraperConfig
        if scroll_steps is not None:
            self.cfg.scroll_steps = scroll_steps
        if headless is not None:
            self.cfg.headless = headless
        self.output_path = output_path
        self.review_output_path = review_output_path
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = ProductExtractor(self.logger)
        self.products: List[Product] = []
        self._session: Optional[requests.Session] = None
        self._review_fetcher: Optional[ReviewFetcher] = None

    def _ensure_review_fetcher(self):
        if self._session is None:
            self._session = make_session(self.cfg)
        if self._review_fetcher is None:
            self._review_fetcher = ReviewFetcher(self._session, self.cfg, self.logger)

    def _handle_response(self, response):
        if "DiscoveryComponentQuery" in response.url and response.request.method == "POST":
            try:
                self.extractor.extract(response.json(), sink=lambda p: self.products.append(p))
            except Exception as e:
                self.logger.error(f"Error parsing JSON: {e}")
    
    def save_product_data_json(self, products: List[Product], out_path: str):
        out = Path(out_path)
        if not products:
            print('No product data to save')
            return
        with out.open('w', encoding='utf-8') as f:
            json.dump(products_to_dict(products), f, ensure_ascii=False, indent=2)
        print(f'Saved {len(products)} products to {out}')
    
    def scrape_products(self):
        self.logger.info(f"Starting product scrape for {len(self.paths)} categories")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.cfg.headless)
            for path in self.paths:
                ctx = browser.new_context()
                page = ctx.new_page()
                page.on("response", self._handle_response)
                page.goto(f"https://www.tokopedia.com/p/{path}", timeout=600000000)
                self.logger.info(f"Loaded category page: {path}")
                try:
                    for _ in range(self.cfg.scroll_steps):
                        page.mouse.wheel(0, 700)
                        page.wait_for_timeout(self.cfg.scroll_delay_ms)
                except Exception as e:
                    self.logger.warning(f"Scroll error in {path}: {e}")
                page.close()
                ctx.close()
                time.sleep(1)  # light pause between categories
            browser.close()
        self.logger.info(f"Scraped {len(self.products)} products")
        self.save_product_data_json(self.products, self.output_path)

    def fetch_and_attach_reviews(self):
        self._ensure_review_fetcher()
        unique_ids = list({p.product_id for p in self.products if p.product_id})
        self.logger.info(f"Fetching reviews for {len(unique_ids)} products in batches of {self.cfg.batch_size}")
        all_reviews: dict[str, list[dict]] = {}
        for batch_ids in batcher(unique_ids, self.cfg.batch_size):
            batch_reviews = self._review_fetcher.fetch_reviews_parallel(batch_ids)
            all_reviews.update(batch_reviews)
            self.logger.info(f"Processed batch of {len(batch_ids)} product_ids")
            time.sleep(self.cfg.after_batch_sleep_sec)
        for prod in self.products:
            prod.reviews = all_reviews.get(prod.product_id, [])
        self.save_product_data_json(self.products, self.review_output_path)
        self.logger.info("Review attachment complete")

    def run(self, include_reviews: bool = True) -> List[Product]:
        self.scrape_products()
        if include_reviews:
            self.fetch_and_attach_reviews()
        return self.products

    def load_products_from_json(self, path: str) -> List[Product]:
        try:
            with Path(path).open('r', encoding='utf-8') as f:
                raw = json.load(f)
            self.products = [
                Product(
                    product_id=str(d.get('product_id', None)),
                    category=d.get('category', ''),
                    name=d.get('name', ''),
                    count_sold=d.get('count_sold', 0),
                    discounted_price=d.get('discounted_price', ''),
                    preorder=d.get('preorder', False),
                    price=d.get('price', ''),
                    stock=d.get('stock', 0),
                    gold_merchant=d.get('gold_merchant', False),
                    is_official=d.get('is_official', False),
                    is_topads=d.get('is_topads', False),
                    rating_average=d.get('rating_average', "0.0"),
                    shop_id=d.get('shop_id', None),
                    shop_location=d.get('shop_location', None),
                    warehouse_id=d.get('warehouse_id', None),
                    url=d.get('url', None),
                    reviews=d.get('reviews') or []
                )
                for d in (raw or [])
            ]
            self.logger.info(f"Loaded {len(self.products)} products from {path}")
            return self.products
        except Exception as e:
            self.logger.error(f"Failed to load products from {path}: {e}")
            return []


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    
    # Small test configuration
    # job = TokopediaScrapeJob(paths = ['buku','dapur'], cfg=ScraperConfig(scroll_steps=1), output_path='product_buku.json', review_output_path='product_buku_with_reviews.json')
    # job.run(include_reviews=True)
    
    #For reciw only
    # job = TokopediaScrapeJob(review_output_path='tokopedia_products_with_review.json')
    # job.fetch_and_attach_reviews


if __name__ == "__main__":
    main()
    
 

# paths = ["rumah-tangga",
#         "audio-kamera-elektronik-lainnya",
#         "buku",
#         "dapur",
#         "elektronik",
#         "fashion-anak-bayi",
#         "fashion-muslim",
#         "fashion-pria",
#         "fashion-wanita",
#         "film-musik",
#         "gaming",
#         "handphone-tablet",
#         "ibu-bayi",
#         "kecantikan",
#         "kesehatan",
#         "komputer-laptop",
#         "logam-mulia",
#         "mainan-hobi",
#         "makanan-minuman",
#         "office-stationery",
#         "olahraga",
#         "otomotif",
#         "perawatan-hewan",
#         "perawatan-tubuh"]    
