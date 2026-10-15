# Graphs Subsystem

## Purpose
This directory contains stateful multi-agent workflows modeled with LangGraph. 

## Architecture
- **State Definition**: Defined in `base.py` as `StockAnalysisState`, typed with reducer functions (`operator.add`) for safe concurrent fan-out and aggregation.
- **Workflow Topology**:
  1. `supervisor_node`: Determines analysis depth and routes to specialized analysts.
  2. `parallel_analysts`: Concurrent execution of Fundamentals, Technicals, and News agents.
  3. `adversarial_debate`: Bull and Bear agents iterate, critiquing each other's assumptions.
  4. `risk_assessment`: Evaluates worst-case scenarios and downside bounds.
  5. `synthesis_node`: Assembles the final markdown report with citations and audit trail.
- **Checkpointing**: In future phases, LangGraph checkpoints will be persisted to PostgreSQL so long-running multi-agent runs can be resumed, audited, and streamed via WebSockets or Server-Sent Events (SSE).
