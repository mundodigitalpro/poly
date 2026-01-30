"""
Tests for the Gamma API client.
"""

import pytest
from unittest.mock import Mock, patch

from bot.gamma_client import GammaClient


class TestGammaClient:
    """Tests for GammaClient."""

    def test_init_creates_session(self):
        """GammaClient initializes with a requests session."""
        client = GammaClient()
        assert client.session is not None
        assert client.BASE_URL == "https://gamma-api.polymarket.com"

    def test_init_accepts_logger(self):
        """GammaClient accepts optional logger."""
        logger = Mock()
        client = GammaClient(logger=logger)
        assert client.logger == logger

    def test_safe_float_handles_none(self):
        """_safe_float returns default for None."""
        client = GammaClient()
        assert client._safe_float(None) == 0.0
        assert client._safe_float(None, 5.0) == 5.0

    def test_safe_float_handles_valid_numbers(self):
        """_safe_float converts valid numbers."""
        client = GammaClient()
        assert client._safe_float(42) == 42.0
        assert client._safe_float("3.14") == 3.14
        assert client._safe_float(0) == 0.0

    def test_safe_float_handles_invalid_input(self):
        """_safe_float returns default for invalid input."""
        client = GammaClient()
        assert client._safe_float("not a number") == 0.0
        assert client._safe_float({}) == 0.0

    def test_normalize_markets_extracts_fields(self):
        """_normalize_markets extracts key fields correctly."""
        client = GammaClient()
        raw = [
            {
                "conditionId": "abc123",
                "slug": "test-market",
                "question": "Test question?",
                "clobTokenIds": ["token1", "token2"],
                "volumeNum": 1000.5,
                "volume24hr": 500.25,
                "liquidityNum": 2000.0,
                "bestBid": 0.45,
                "bestAsk": 0.55,
                "spread": 0.10,
                "active": True,
                "closed": False,
            }
        ]

        normalized = client._normalize_markets(raw)

        assert len(normalized) == 1
        m = normalized[0]
        assert m["condition_id"] == "abc123"
        assert m["slug"] == "test-market"
        assert m["question"] == "Test question?"
        assert m["clob_token_ids"] == ["token1", "token2"]
        assert m["volume_total"] == 1000.5
        assert m["volume_24h"] == 500.25
        assert m["liquidity"] == 2000.0
        assert m["best_bid"] == 0.45
        assert m["best_ask"] == 0.55
        assert m["spread"] == 0.10
        assert m["active"] is True
        assert m["closed"] is False

    def test_normalize_markets_handles_json_string_token_ids(self):
        """_normalize_markets handles clobTokenIds as JSON string."""
        client = GammaClient()
        raw = [{"clobTokenIds": '["token1", "token2"]'}]

        normalized = client._normalize_markets(raw)

        assert normalized[0]["clob_token_ids"] == ["token1", "token2"]

    def test_normalize_markets_handles_missing_fields(self):
        """_normalize_markets handles missing fields gracefully."""
        client = GammaClient()
        raw = [{}]

        normalized = client._normalize_markets(raw)

        assert len(normalized) == 1
        m = normalized[0]
        assert m["condition_id"] is None
        assert m["volume_24h"] == 0.0
        assert m["clob_token_ids"] == []

    @patch.object(GammaClient, "_get")
    def test_get_markets_returns_normalized_data(self, mock_get):
        """get_markets returns normalized market data."""
        mock_get.return_value = [
            {"conditionId": "abc", "volumeNum": 100, "clobTokenIds": ["t1"]}
        ]

        client = GammaClient()
        markets = client.get_markets(limit=1)

        assert len(markets) == 1
        assert markets[0]["condition_id"] == "abc"
        assert markets[0]["volume_total"] == 100

    @patch.object(GammaClient, "_get")
    def test_get_markets_handles_paginated_response(self, mock_get):
        """get_markets handles paginated response format."""
        mock_get.return_value = {
            "data": [{"conditionId": "abc", "volumeNum": 100, "clobTokenIds": []}]
        }

        client = GammaClient()
        markets = client.get_markets()

        assert len(markets) == 1

    @patch.object(GammaClient, "_get")
    def test_get_markets_returns_empty_on_failure(self, mock_get):
        """get_markets returns empty list on API failure."""
        mock_get.return_value = None

        client = GammaClient()
        markets = client.get_markets()

        assert markets == []

    @patch.object(GammaClient, "get_markets")
    def test_get_top_volume_markets_filters_correctly(self, mock_get_markets):
        """get_top_volume_markets filters by volume and liquidity."""
        mock_get_markets.return_value = [
            {"volume_24h": 1000, "liquidity": 2000, "clob_token_ids": ["t1"]},
            {"volume_24h": 100, "liquidity": 2000, "clob_token_ids": ["t2"]},  # Low vol
            {"volume_24h": 1000, "liquidity": 100, "clob_token_ids": ["t3"]},  # Low liq
            {"volume_24h": 1000, "liquidity": 2000, "clob_token_ids": []},  # No tokens
        ]

        client = GammaClient()
        markets = client.get_top_volume_markets(
            min_volume_24h=500, min_liquidity=1000
        )

        assert len(markets) == 1
        assert markets[0]["clob_token_ids"] == ["t1"]


class TestGammaClientIntegration:
    """Integration tests for GammaClient (requires network)."""

    @pytest.mark.integration
    def test_get_markets_real_api(self):
        """Test against real Gamma API (skip in CI)."""
        client = GammaClient()
        markets = client.get_markets(limit=3)

        assert len(markets) <= 3
        if markets:
            m = markets[0]
            assert "condition_id" in m
            assert "volume_24h" in m
            assert "liquidity" in m
