import logging
import re
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Iterable, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class Product:
    product_id: str
    category: str
    name: Optional[str]
    count_sold: Optional[int]
    discounted_price: Optional[str]
    preorder: Optional[bool]
    price: Optional[str]
    stock: Optional[int]
    gold_merchant: Optional[bool]
    is_official: Optional[bool]
    is_topads: Optional[bool]
    rating_average: Optional[float]
    shop_id: Optional[str]
    shop_location: Optional[str]
    warehouse_id: Optional[str]
    url: Optional[str]
    reviews: Optional[List[Dict]] = None


@dataclass
class ScraperConfig:
    headless: bool = False
    batch_size: int = 25
    review_limit_per_page: int = 10
    max_workers: int = 8
    scroll_steps: int = 1
    scroll_delay_ms: int = 2000
    after_batch_sleep_sec: float = 2.0
    request_timeout_sec: int = 20
    retry_total: int = 5
    retry_backoff_factor: float = 0.5
    retry_statuses: tuple = (429, 500, 502, 503, 504)
    pool_connections: int = 50
    pool_maxsize: int = 50


def normalize_price(price_str: Optional[str]) -> Optional[str]:
    if price_str is None:
        return None
    return str(price_str).replace('Rp', '').replace('.', '').strip()


def normalize_category(text: str) -> str:
    parts = text.split('_outer_') if text else ["", ""]
    first = parts[0] if parts else ""
    second = parts[1] if len(parts) > 1 else ""
    match = re.search(r'clp_([a-zA-Z0-9_]+?)_([0-9]+)', first)
    first_norm = match.group(1) if match else ""
    second_norm = second[:-7] if len(second) >= 7 else second
    return f"{first_norm}|{second_norm}"


def batcher(iterable: Iterable[str], batch_size: int) -> Iterable[List[str]]:
    items = list(iterable)
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def make_session(cfg: ScraperConfig) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=cfg.retry_total,
        connect=cfg.retry_total,
        read=cfg.retry_total,
        backoff_factor=cfg.retry_backoff_factor,
        status_forcelist=list(cfg.retry_statuses),
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=cfg.pool_connections, pool_maxsize=cfg.pool_maxsize)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


class ReviewFetcher:
    def __init__(self, session: requests.Session, cfg: ScraperConfig, logger: Optional[logging.Logger] = None):
        self.session = session
        self.cfg = cfg
        self.logger = logger or logging.getLogger(__name__)

    def fetch_reviews_for_product(self, product_id: str) -> List[Dict]:
        page = 1
        all_reviews: List[Dict] = []
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        while True:
            payload = [
                {
                    "operationName": "productReviewList",
                    "variables": {
                        "productID": str(product_id),
                        "page": page,
                        "limit": self.cfg.review_limit_per_page,
                        "sortBy": "create_time desc",
                        "filterBy": ""
                    },
                    "query": """
    query productReviewList($productID: String!, $page: Int!, $limit: Int!, $sortBy: String, $filterBy: String) {
      productrevGetProductReviewList(productID: $productID, page: $page, limit: $limit, sortBy: $sortBy, filterBy: $filterBy) {
        productID
        list {
          id: feedbackID
          variantName
          message
          productRating
          reviewCreateTime
          reviewCreateTimestamp
          isReportable
          isAnonymous
          imageAttachments { attachmentID imageThumbnailUrl imageUrl __typename }
          videoAttachments { attachmentID videoUrl __typename }
          reviewResponse { message createTime __typename }
          user { userID fullName image url __typename }
          likeDislike { totalLike likeStatus __typename }
          stats { key formatted count __typename }
          badRatingReasonFmt
          __typename
        }
        shop { shopID name url image __typename }
        hasNext
        totalReviews
        __typename
      }
    }
    """
                }
            ]
            try:
                resp = self.session.post(
                    "https://gql.tokopedia.com/graphql/productReviewList",
                    headers=headers,
                    json=payload,
                    timeout=self.cfg.request_timeout_sec,
                )
                self.logger.info(f"Fetched page {page} for product {product_id}, status: {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.logger.error(f"Error fetching reviews for product {product_id} page {page}: {e}")
                break

            if not isinstance(data, list) or not data:
                break
            reviews_data = data[0].get("data", {}).get("productrevGetProductReviewList", {})
            reviews_list = reviews_data.get("list", [])
            for review in reviews_list:
                review_obj = {
                    "review_id": review.get("id", 0),
                    "variant_name": review.get("variantName", ""),
                    "message": review.get("message", ""),
                    "rating": review.get("productRating", ""),
                    "review_time": review.get("reviewCreateTime", ""),
                    "review_timestamp": review.get("reviewCreateTimestamp", 0),
                    "review_response": (review.get("reviewResponse", {})).get("message", ""),
                    "like_dislike": (review.get("likeDislike", {})).get("totalLike", 0),
                    "bad_rating_reason": review.get("badRatingReasonFmt", ""),
                }
                all_reviews.append(review_obj)

            if not reviews_data.get("hasNext"):
                self.logger.info(f"No more pages for product {product_id}. Total reviews: {reviews_data.get('totalReviews')}")
                break
            page += 1
        return all_reviews

    def fetch_reviews_parallel(self, product_ids: List[str]) -> Dict[str, List[Dict]]:
        results: Dict[str, List[Dict]] = {}
        workers = max(1, self.cfg.max_workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_pid = {executor.submit(self.fetch_reviews_for_product, pid): pid for pid in product_ids}
            for future in as_completed(future_to_pid):
                pid = future_to_pid[future]
                try:
                    reviews = future.result()
                    results[pid] = reviews
                except Exception as exc:
                    self.logger.error(f"Error fetching reviews for product {pid}: {exc}")
                    results[pid] = []
        return results


class ProductExtractor:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def extract(self, discovery_json: List[Dict], sink: Callable[[Product], None]) -> None:
        if discovery_json is None:
            raise RuntimeError('JSON data not loaded.')
        for item in discovery_json:
            comp = item.get('data', {}).get('componentInfo', {}).get('data', {}).get('component', {})
            comp_data = comp.get('data', [])
            if isinstance(comp_data, list):
                for p in comp_data:
                    prod = Product(
                        product_id=str(p.get('product_id', None)),
                        category=normalize_category(p.get('source_module', "")),
                        name=p.get('name', ""),
                        count_sold=p.get('count_sold', 0),
                        discounted_price=normalize_price(p.get('discounted_price', "")),
                        preorder=p.get('preorder', False),
                        price=normalize_price(p.get('price', "")),
                        stock=p.get('stock', 0),
                        gold_merchant=p.get('gold_merchant', False),
                        is_official=p.get('is_official', False),
                        is_topads=p.get('is_topads', False),
                        rating_average=p.get('rating_average', "0.0"),
                        shop_id=p.get('shop_id', None),
                        shop_location=p.get('shop_location', ""),
                        warehouse_id=p.get('warehouse_id', None),
                        url=p.get('url_desktop', ""),
                        reviews=None,
                    )
                    sink(prod)

def assign_reviews(products: List[Product], reviews_map: Dict[str, List[Dict]]):
    for prod in products:
        prod.reviews = reviews_map.get(prod.product_id, [])


def products_to_dict(products: List[Product]) -> List[Dict]:
    out = []
    for p in products:
        out.append({
            'product_id': p.product_id,
            'category': p.category,
            'name': p.name,
            'count_sold': p.count_sold,
            'discounted_price': p.discounted_price,
            'preorder': p.preorder,
            'price': p.price,
            'stock': p.stock,
            'gold_merchant': p.gold_merchant,
            'is_official': p.is_official,
            'is_topads': p.is_topads,
            'rating_average': p.rating_average,
            'shop_id': p.shop_id,
            'shop_location': p.shop_location,
            'warehouse_id': p.warehouse_id,
            'url': p.url,
            'reviews': p.reviews or [],
        })
    return out
