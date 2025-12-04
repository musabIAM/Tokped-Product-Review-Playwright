"""Unit tests for scraper module."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from dataclasses import asdict

from scraper import (
    Product,
    ScraperConfig,
    normalize_price,
    normalize_category,
    batcher,
    make_session,
    ReviewFetcher,
    ProductExtractor,
    products_to_dict,
)


class TestDataModels(unittest.TestCase):
    def test_product_dataclass(self):
        prod = Product(
            product_id="123",
            category="test|category",
            name="Test Product",
            count_sold=100,
            discounted_price="50000",
            preorder=False,
            price="100000",
            stock=10,
            gold_merchant=True,
            is_official=False,
            is_topads=True,
            rating_average=4.5,
            shop_id="shop123",
            shop_location="Jakarta",
            warehouse_id="wh001",
            url="https://example.com/prod",
            reviews=[]
        )
        self.assertEqual(prod.product_id, "123")
        self.assertEqual(prod.name, "Test Product")
        self.assertEqual(prod.reviews, [])

    def test_scraper_config_defaults(self):
        cfg = ScraperConfig()
        self.assertFalse(cfg.headless)
        self.assertEqual(cfg.batch_size, 25)
        self.assertEqual(cfg.max_workers, 8)
        self.assertEqual(cfg.retry_total, 5)

    def test_scraper_config_custom(self):
        cfg = ScraperConfig(headless=False, batch_size=50, max_workers=10)
        self.assertFalse(cfg.headless)
        self.assertEqual(cfg.batch_size, 50)
        self.assertEqual(cfg.max_workers, 10)


class TestHelpers(unittest.TestCase):
    def test_normalize_price_with_rupiah(self):
        self.assertEqual(normalize_price("Rp1.000.000"), "1000000")
        self.assertEqual(normalize_price("Rp50.000"), "50000")
        self.assertEqual(normalize_price("Rp100"), "100")

    def test_normalize_price_already_normalized(self):
        self.assertEqual(normalize_price("1000000"), "1000000")

    def test_normalize_price_none(self):
        self.assertIsNone(normalize_price(None))

    def test_normalize_category(self):
        input_text = "clp_electronics_12345_outer_smartphones_123456"
        result = normalize_category(input_text)
        self.assertEqual(result, "electronics|smartphones")

    def test_normalize_category_no_match(self):
        input_text = "invalid_outer_test_1234567"
        result = normalize_category(input_text)
        self.assertEqual(result, "|test")

    def test_batcher(self):
        items = ["a", "b", "c", "d", "e", "f", "g"]
        batches = list(batcher(items, 3))
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0], ["a", "b", "c"])
        self.assertEqual(batches[1], ["d", "e", "f"])
        self.assertEqual(batches[2], ["g"])

    def test_batcher_empty(self):
        batches = list(batcher([], 5))
        self.assertEqual(batches, [])

    def test_make_session(self):
        cfg = ScraperConfig(retry_total=3, pool_connections=20, pool_maxsize=20)
        session = make_session(cfg)
        self.assertIsInstance(session, requests.Session)
        # Verify adapter is mounted
        adapter = session.get_adapter("https://example.com")
        self.assertIsNotNone(adapter)


class TestProductExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = ProductExtractor()
        self.sink_products = []

    def test_extract_valid_data(self):
        mock_json = [
            {
                "data": {
                    "componentInfo": {
                        "data": {
                            "component": {
                                "data": [
                                    {
                                        "product_id": 123,
                                        "source_module": "ops_discovery_clp_books_984_outer_fiction_module",
                                        "name": "Test Book",
                                        "count_sold": 50,
                                        "discounted_price": "Rp50.000",
                                        "preorder": False,
                                        "price": "Rp100.000",
                                        "stock": 10,
                                        "gold_merchant": True,
                                        "is_official": False,
                                        "is_topads": False,
                                        "rating_average": "4.8",
                                        "shop_id": 123456,
                                        "shop_location": "Jakarta",
                                        "warehouse_id": 12345,
                                        "url_desktop": "https://example.com/book"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        ]
        self.extractor.extract(mock_json, sink=lambda p: self.sink_products.append(p))
        self.assertEqual(len(self.sink_products), 1)
        prod = self.sink_products[0]
        self.assertEqual(prod.product_id, 123)
        self.assertEqual(prod.name, "Test Book")
        self.assertEqual(prod.price, "100000")
        self.assertEqual(prod.discounted_price, "50000")
        self.assertEqual(prod.category, "books|fiction")

    def test_extract_empty_data(self):
        mock_json = []
        self.extractor.extract(mock_json, sink=lambda p: self.sink_products.append(p))
        self.assertEqual(len(self.sink_products), 0)

    def test_extract_none_raises(self):
        with self.assertRaises(RuntimeError):
            self.extractor.extract(None, sink=lambda p: None)


class TestReviewFetcher(unittest.TestCase):
    def setUp(self):
        self.cfg = ScraperConfig(review_limit_per_page=10, max_workers=2)
        self.mock_session = MagicMock(spec=requests.Session)
        self.fetcher = ReviewFetcher(self.mock_session, self.cfg)

    def test_fetch_reviews_for_product_single_page(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "data": {
                    "productrevGetProductReviewList": {
                        "list": [
                            {
                                "id": "rev001",
                                "variantName": "Color: Red",
                                "message": "Great product!",
                                "productRating": 5,
                                "reviewCreateTime": "1 Bulan yang lalu",
                                "reviewCreateTimestamp": 1704067200,
                                "reviewResponse": {"message": "Thank you!"},
                                "likeDislike": {"totalLike": 10},
                                "badRatingReasonFmt": None
                            }
                        ],
                        "hasNext": False,
                        "totalReviews": 1
                    }
                }
            }
        ]
        self.mock_session.post.return_value = mock_response

        reviews = self.fetcher.fetch_reviews_for_product("123")
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["review_id"], "rev001")
        self.assertEqual(reviews[0]["message"], "Great product!")
        self.assertEqual(reviews[0]["rating"], 5)

    def test_fetch_reviews_for_product_multiple_pages(self):
        # First page
        mock_resp1 = Mock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = [
            {
                "data": {
                    "productrevGetProductReviewList": {
                        "list": [{"id": "rev001", "variantName": None, "message": "Review 1", "productRating": 5,
                                 "reviewCreateTime": "1 Bulan yang lalu", "reviewCreateTimestamp": 1704067200,
                                 "reviewResponse": None, "likeDislike": None, "badRatingReasonFmt": None}],
                        "hasNext": True,
                        "totalReviews": 2
                    }
                }
            }
        ]
        # Second page
        mock_resp2 = Mock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = [
            {
                "data": {
                    "productrevGetProductReviewList": {
                        "list": [{"id": "rev002", "variantName": None, "message": "Review 2", "productRating": 4,
                                 "reviewCreateTime": "1 Bulan yang lalu", "reviewCreateTimestamp": 1704153600,
                                 "reviewResponse": None, "likeDislike": None, "badRatingReasonFmt": None}],
                        "hasNext": False,
                        "totalReviews": 2
                    }
                }
            }
        ]
        self.mock_session.post.side_effect = [mock_resp1, mock_resp2]

        reviews = self.fetcher.fetch_reviews_for_product("123")
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]["review_id"], "rev001")
        self.assertEqual(reviews[1]["review_id"], "rev002")

    def test_fetch_reviews_parallel(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "data": {
                    "productrevGetProductReviewList": {
                        "list": [{"id": "rev001", "variantName": None, "message": "Test", "productRating": 5,
                                 "reviewCreateTime": "1 Bulan yang lalu", "reviewCreateTimestamp": 1704067200,
                                 "reviewResponse": None, "likeDislike": None, "badRatingReasonFmt": None}],
                        "hasNext": False,
                        "totalReviews": 1
                    }
                }
            }
        ]
        self.mock_session.post.return_value = mock_response

        results = self.fetcher.fetch_reviews_parallel(["123", "456"])
        self.assertIn("123", results)
        self.assertIn("456", results)
        self.assertEqual(len(results["123"]), 1)
        self.assertEqual(len(results["456"]), 1)


class TestProductsToDict(unittest.TestCase):
    def test_products_to_dict(self):
        products = [
            Product(
                product_id="123",
                category="test|cat",
                name="Product 1",
                count_sold=10,
                discounted_price="50000",
                preorder=False,
                price="100000",
                stock=5,
                gold_merchant=True,
                is_official=False,
                is_topads=False,
                rating_average=4.5,
                shop_id="shop1",
                shop_location="Jakarta",
                warehouse_id="wh1",
                url="https://example.com/1",
                reviews=[{"review_id": "rev1"}]
            )
        ]
        result = products_to_dict(products)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["product_id"], "123")
        self.assertEqual(result[0]["name"], "Product 1")
        self.assertEqual(result[0]["reviews"], [{"review_id": "rev1"}])

    def test_products_to_dict_empty(self):
        result = products_to_dict([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
