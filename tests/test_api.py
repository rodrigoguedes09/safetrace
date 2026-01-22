"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a test client."""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client: TestClient) -> None:
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health(self, client: TestClient) -> None:
        """Test health endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "cache_status" in data


class TestChainsEndpoint:
    """Tests for chains endpoint."""

    def test_list_chains(self, client: TestClient) -> None:
        """Test listing supported chains."""
        response = client.get("/api/v1/chains")
        
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data
        assert "count" in data
        assert data["count"] > 40  # 41+ chains supported
        
        # Verify chain structure
        chain = data["chains"][0]
        assert "slug" in chain
        assert "name" in chain
        assert "symbol" in chain
        assert "type" in chain


class TestStatsEndpoint:
    """Tests for stats endpoint."""

    def test_stats(self, client: TestClient) -> None:
        """Test stats endpoint."""
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "supported_chains_count" in data


class TestTraceEndpoint:
    """Tests for trace endpoint."""

    def test_trace_invalid_chain(self, client: TestClient) -> None:
        """Test tracing with invalid chain."""
        response = client.post(
            "/api/v1/compliance/trace",
            json={
                "tx_hash": "0x" + "a" * 64,
                "chain": "invalid_chain",
                "depth": 3,
            },
        )
        
        assert response.status_code == 400
        assert "Unsupported blockchain" in response.json()["detail"]

    def test_trace_invalid_depth(self, client: TestClient) -> None:
        """Test tracing with invalid depth."""
        response = client.post(
            "/api/v1/compliance/trace",
            json={
                "tx_hash": "0x" + "b" * 64,
                "chain": "ethereum",
                "depth": 15,
            },
        )
        
        assert response.status_code == 422  # Validation error


class TestDownloadEndpoint:
    """Tests for download endpoint."""

    def test_download_not_found(self, client: TestClient) -> None:
        """Test downloading nonexistent certificate."""
        response = client.get("/api/v1/compliance/download/nonexistent.pdf")
        
        assert response.status_code == 404

    def test_download_invalid_type(self, client: TestClient) -> None:
        """Test downloading invalid file type."""
        response = client.get("/api/v1/compliance/download/file.txt")
        
        assert response.status_code == 400
