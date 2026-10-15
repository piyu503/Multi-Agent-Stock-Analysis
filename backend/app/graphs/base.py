from typing import Annotated, Any, Dict, List, Optional, TypedDict
import operator


class StockAnalysisState(TypedDict):
    """LangGraph multi-agent state schema for stock analysis runs."""

    ticker: str
    company_name: Optional[str]
    raw_financials: Dict[str, Any]
    research_notes: Annotated[List[Dict[str, Any]], operator.add]
    bull_arguments: List[str]
    bear_arguments: List[str]
    risk_factors: List[str]
    valuation_model: Dict[str, Any]
    final_report_markdown: Optional[str]
    confidence_score: float
    citations: Annotated[List[str], operator.add]
    errors: Annotated[List[str], operator.add]
