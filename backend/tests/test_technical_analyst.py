"""Unit and integration tests for TechnicalAnalystService and the technical analysis API endpoint."""

from unittest.mock import AsyncMock, patch
import pandas as pd
import pytest
from httpx import AsyncClient

from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import LLMConnectionError, LLMTimeoutError
from app.schemas.technical_analysis import TechnicalInterpretation
from app.services.market_data_service import MarketDataService
from app.services.technical_analyst import TechnicalAnalystService
from tests.test_market_data import create_sample_ohlcv


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider returning controlled TechnicalInterpretation outputs."""

    def __init__(self, interpretation: TechnicalInterpretation) -> None:
        super().__init__(model_name="deepseek-r1:7b", provider_name="ollama")
        self.interpretation = interpretation
        self.last_prompt = ""

    async def generate(self, prompt: str, system_prompt=None, temperature=0.2) -> str:
        return "mocked text"

    async def generate_structured(self, prompt: str, response_model, system_prompt=None, temperature=0.2):
        self.last_prompt = prompt
        return self.interpretation

    async def check_health(self):
        return {"status": "ok", "provider": "ollama", "configured_model": "deepseek-r1:7b"}


@pytest.fixture
def sample_interpretation() -> TechnicalInterpretation:
    return TechnicalInterpretation(
        bullish_signals=["Trading above 20-session SMA (INR 2143.35)", "Strong momentum with +4.89% daily return"],
        bearish_signals=["Elevated annualized volatility at 39.0%"],
        trend_interpretation="Bullish alignment above 20-day moving average.",
        risk_factors=["High historical volatility indicates potential wide intraday price swings."],
        missing_data=["50-session SMA unavailable due to limited history (< 50 bars)"],
        uncertainties=["Directional continuation depends on holding above recent support."],
        evidence=["Latest Close: INR 2465.00", "20-SMA: INR 2143.35", "20-Session Volatility: 39.0%"],
        conclusion=(
            "The technical structure demonstrates short-term upward momentum above the 20-SMA. "
            "However, elevated volatility warrants strict risk management. This analysis is historical and informational."
        ),
    )


class TestTechnicalAnalystService:
    @pytest.mark.asyncio
    async def test_technical_analyst_end_to_end(self, sample_interpretation: TechnicalInterpretation):
        mock_df = create_sample_ohlcv(days=60, base_price=2000.0, daily_increment=5.0)
        mock_info = {
            "name": "Tata Consultancy Services Limited",
            "currency": "INR",
            "exchange": "NSI",
        }

        mock_provider = MockLLMProvider(sample_interpretation)
        service = TechnicalAnalystService(llm_provider=mock_provider)

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, mock_info),
        ):
            resp = await service.analyze(ticker="TCS", period="6mo")

            assert resp.ticker == "TCS"
            assert resp.resolved_ticker == "TCS.NS"
            assert resp.provider == "ollama"
            assert resp.model == "deepseek-r1:7b"
            assert resp.company_name == "Tata Consultancy Services Limited"

            # Verify deterministic price and indicator values were not fabricated by LLM
            assert resp.price_summary.latest_close is not None
            assert resp.indicator_summary.sma_20 is not None
            assert resp.indicator_summary.sma_50 is not None

            # Verify LLM interpretation fields
            assert len(resp.bullish_signals) == 2
            assert "above 20-session SMA" in resp.bullish_signals[0]
            assert "elevated volatility warrants" in resp.conclusion.lower()
            assert "informational" in resp.disclaimer.lower()

            # Verify factual prompt contained exact numbers
            assert "TCS.NS" in mock_provider.last_prompt
            assert "FACTS:" in mock_provider.last_prompt

    @pytest.mark.asyncio
    async def test_technical_analyst_preserves_missing_data_without_fabrication(
        self, sample_interpretation: TechnicalInterpretation
    ):
        # 10 days of data (< 20 for SMA-20, < 50 for SMA-50)
        mock_df = create_sample_ohlcv(days=10, base_price=2000.0)
        mock_provider = MockLLMProvider(sample_interpretation)
        service = TechnicalAnalystService(llm_provider=mock_provider)

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, {}),
        ):
            resp = await service.analyze(ticker="TCS", period="1mo")

            assert resp.indicator_summary.sma_20 is None
            assert resp.indicator_summary.sma_50 is None
            assert resp.indicator_summary.volatility_20_annualized_pct is None
            assert "Unavailable (requires 20 bars)" in mock_provider.last_prompt


@pytest.mark.asyncio
class TestTechnicalAnalysisApi:
    async def test_api_technical_analysis_success(self, client: AsyncClient, sample_interpretation: TechnicalInterpretation):
        mock_df = create_sample_ohlcv(days=60)
        mock_info = {"name": "Tata Consultancy Services Limited", "currency": "INR"}

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, mock_info),
        ), patch(
            "app.services.technical_analyst.get_llm_provider",
            return_value=MockLLMProvider(sample_interpretation),
        ):
            resp = await client.post(
                "/api/v1/analysis/technical",
                json={"ticker": "TCS", "period": "6mo"},
            )
            assert resp.status_code == 200
            data = resp.json()

            assert data["ticker"] == "TCS"
            assert data["resolved_ticker"] == "TCS.NS"
            assert data["provider"] == "ollama"
            assert data["model"] == "deepseek-r1:7b"
            assert len(data["bullish_signals"]) > 0
            assert "conclusion" in data

    async def test_api_technical_analysis_provider_connection_error_returns_503(
        self, client: AsyncClient
    ):
        mock_df = create_sample_ohlcv(days=60)
        mock_provider = AsyncMock()
        mock_provider.generate_structured.side_effect = LLMConnectionError(
            "Connection refused to Ollama", provider="ollama"
        )
        mock_provider.provider_name = "ollama"
        mock_provider.model_name = "deepseek-r1:7b"

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, {}),
        ), patch(
            "app.services.technical_analyst.get_llm_provider",
            return_value=mock_provider,
        ):
            resp = await client.post(
                "/api/v1/analysis/technical",
                json={"ticker": "TCS", "period": "6mo"},
            )
            assert resp.status_code == 503
            assert "Local LLM provider unavailable" in resp.json()["detail"]

    async def test_api_technical_analysis_timeout_returns_504(self, client: AsyncClient):
        mock_df = create_sample_ohlcv(days=60)
        mock_provider = AsyncMock()
        mock_provider.generate_structured.side_effect = LLMTimeoutError(
            "Model inference timed out", provider="ollama"
        )
        mock_provider.provider_name = "ollama"
        mock_provider.model_name = "deepseek-r1:7b"

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, {}),
        ), patch(
            "app.services.technical_analyst.get_llm_provider",
            return_value=mock_provider,
        ):
            resp = await client.post(
                "/api/v1/analysis/technical",
                json={"ticker": "TCS", "period": "6mo"},
            )
            assert resp.status_code == 504
            assert "timed out" in resp.json()["detail"]

    async def test_api_provider_status_endpoint(self, client: AsyncClient):
        mock_provider = AsyncMock()
        mock_provider.check_health.return_value = {
            "status": "ok",
            "provider": "ollama",
            "configured_model": "deepseek-r1:7b",
            "model_installed": True,
        }

        with patch(
            "app.api.v1.analysis.get_llm_provider",
            return_value=mock_provider,
        ):
            resp = await client.get("/api/v1/analysis/provider-status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["provider"] == "ollama"
            assert data["configured_model"] == "deepseek-r1:7b"
