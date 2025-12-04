"""Unit tests for main module (TokopediaScrapeJob)."""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
from pathlib import Path

from main import TokopediaScrapeJob
from scraper import ScraperConfig, Product


class TestTokopediaScrapeJob(unittest.TestCase):
    def test_init_default_config(self):
        job = TokopediaScrapeJob(paths=["test"])
        self.assertEqual(job.paths, ["test"])
        self.assertEqual(job.cfg, ScraperConfig)  # When cfg=None, it defaults to ScraperConfig class
        self.assertEqual(job.output_path, "product_data.json")
        self.assertEqual(job.products, [])

    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_save_product_data_json(self, mock_print, mock_path_open):
        job = TokopediaScrapeJob(paths=[])
        products = [
            Product(
                product_id="123",
                category="test|cat",
                name="Test",
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
                url="https://example.com",
                reviews=[]
            )
        ]
        job.save_product_data_json(products, "test_output.json")
        mock_path_open.assert_called_once()

    @patch("builtins.print")
    def test_save_empty_products(self, mock_print):
        job = TokopediaScrapeJob(paths=[])
        # Should not raise, just print message
        job.save_product_data_json([], "test_output.json")
        mock_print.assert_called_once_with("No product data to save")

    def test_init_custom_config(self):
        cfg = ScraperConfig(headless=True, batch_size=50)
        job = TokopediaScrapeJob(
            paths=["test1", "test2"],
            cfg=cfg,
            output_path="custom_out.json",
            review_output_path="custom_reviews.json"
        )
        self.assertEqual(job.paths, ["test1", "test2"])
        self.assertTrue(job.cfg.headless)
        self.assertEqual(job.cfg.batch_size, 50)
        self.assertEqual(job.output_path, "custom_out.json")

    def test_init_override_scroll_steps(self):
        cfg = ScraperConfig()
        job = TokopediaScrapeJob(paths=["test"], cfg=cfg, scroll_steps=5)
        self.assertEqual(job.cfg.scroll_steps, 5)

    def test_init_override_headless(self):
        cfg = ScraperConfig()
        job = TokopediaScrapeJob(paths=["test"], cfg=cfg, headless=True)
        self.assertTrue(job.cfg.headless)

    @patch("pathlib.Path.open", new_callable=mock_open, read_data='[{"product_id": "123", "category": "test|cat", "name": "Product1", "count_sold": 10, "price": "100000", "discounted_price": "50000", "preorder": false, "stock": 5, "gold_merchant": true, "is_official": false, "is_topads": false, "rating_average": 4.5, "shop_id": "shop1", "shop_location": "Jakarta", "warehouse_id": "wh1", "url": "https://example.com", "reviews": []}]')
    def test_load_products_from_json(self, mock_file):
        job = TokopediaScrapeJob(paths=[])
        products = job.load_products_from_json("test_products.json")
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].product_id, "123")
        self.assertEqual(products[0].name, "Product1")
        self.assertEqual(len(job.products), 1)

    @patch("pathlib.Path.open", side_effect=FileNotFoundError)
    def test_load_products_from_json_file_not_found(self, mock_file):
        job = TokopediaScrapeJob(paths=[])
        products = job.load_products_from_json("nonexistent.json")
        self.assertEqual(products, [])
        self.assertEqual(len(job.products), 0)

    @patch("main.ReviewFetcher")
    @patch("main.make_session")
    def test_fetch_and_attach_reviews(self, mock_make_session, mock_fetcher_class):
        job = TokopediaScrapeJob(paths=[], review_output_path="test_reviews.json")
        job.products = [
            Product(
                product_id="123",
                category="test|cat",
                name="Test",
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
                url="https://example.com",
                reviews=None
            )
        ]
        
        mock_session = MagicMock()
        mock_make_session.return_value = mock_session
        
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_reviews_parallel.return_value = {
            "123": [{"review_id": "rev1", "message": "Great!"}]
        }
        mock_fetcher_class.return_value = mock_fetcher
        
        with patch.object(job, 'save_product_data_json'):
            job.fetch_and_attach_reviews()
        
        self.assertIsNotNone(job.products[0].reviews)
        self.assertEqual(len(job.products[0].reviews), 1)
        self.assertEqual(job.products[0].reviews[0]["review_id"], "rev1")

    def test_handle_response_valid(self):
        job = TokopediaScrapeJob(paths=[])
        mock_response = Mock()
        mock_response.url = "https://gql.tokopedia.com/DiscoveryComponentQuery"
        mock_response.request.method = "POST"
        mock_response.json.return_value = [
            {
                "data": {
                    "componentInfo": {
                        "data": {
                            "component": {
                                "data": [
                                    {
                                        "product_id": "999",
                                        "source_module": "clp_test_001_outer_test_1234567",
                                        "name": "Test Product",
                                        "count_sold": 5,
                                        "discounted_price": None,
                                        "preorder": False,
                                        "price": "50000",
                                        "stock": 2,
                                        "gold_merchant": False,
                                        "is_official": True,
                                        "is_topads": False,
                                        "rating_average": 4.0,
                                        "shop_id": "shop999",
                                        "shop_location": "Bandung",
                                        "warehouse_id": "wh999",
                                        "url_desktop": "https://example.com/999"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        ]
        
        job._handle_response(mock_response)
        self.assertEqual(len(job.products), 1)
        self.assertEqual(job.products[0].product_id, "999")
        self.assertEqual(job.products[0].name, "Test Product")

    def test_handle_response_invalid_url(self):
        job = TokopediaScrapeJob(paths=[])
        mock_response = Mock()
        mock_response.url = "https://example.com/other"
        mock_response.request.method = "POST"
        
        job._handle_response(mock_response)
        self.assertEqual(len(job.products), 0)


if __name__ == "__main__":
    unittest.main()
