import pytest
from httpx import ASGITransport, AsyncClient
from app.database.session import get_db_session
from app.main import create_app
from app.schemas.health import HealthStatus


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient):
    """Test health check returns HEALTHY when database dependency responds."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == HealthStatus.HEALTHY
    assert "app" in data
    assert data["app"]["status"] == "ok"
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert data["dependencies"]["database"]["status"] == HealthStatus.HEALTHY
    assert data["dependencies"]["database"]["latency_ms"] is not None


@pytest.mark.asyncio
async def test_health_check_convenience_alias(client: AsyncClient):
    """Test that /api/health acts as a valid direct convenience alias."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_check_degraded_when_db_fails():
    """Test health check reports DEGRADED when database fails, without crashing the server."""
    app = create_app()

    # Override DB to simulate an unavailable connection
    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionRefusedError("Simulated PostgreSQL connection failure")

    async def override_broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db_session] = override_broken_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as broken_client:
        response = await broken_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        # Application distinguishes its own health from dependency health
        assert data["status"] == HealthStatus.DEGRADED
        assert data["app"]["status"] == "ok"
        assert data["dependencies"]["database"]["status"] == HealthStatus.UNHEALTHY
        assert "Database ping failed" in data["dependencies"]["database"]["message"]
