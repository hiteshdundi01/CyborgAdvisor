"""
FastAPI Backend for CyborgAdvisor SaaS

Provides REST API endpoints for:
- Portfolio management (CRUD)
- Rebalance saga execution
- Tax Loss Harvesting saga execution
- Real-time saga status via WebSocket/SSE
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json
from datetime import datetime
from contextlib import asynccontextmanager

# Import saga modules
import sys
sys.path.insert(0, "..")
from src.sagas import (
    RebalanceSaga,
    TaxLossHarvestingSaga,
    SagaStatus,
    SagaContext,
)
from src.sagas.tax_loss_harvesting import (
    is_substantially_identical,
    get_replacement_suggestions,
    FUND_FAMILY_MAPPING,
)


# =============================================================================
# Pydantic Models
# =============================================================================

class PortfolioHolding(BaseModel):
    asset: str
    asset_class: str
    value: float
    quantity: Optional[float] = None


class Portfolio(BaseModel):
    holdings: list[PortfolioHolding]
    total_value: float
    cash: float = 0


class TargetAllocation(BaseModel):
    stocks: float = 0.6
    bonds: float = 0.3
    cash: float = 0.05
    alternatives: float = 0.05


class RebalanceRequest(BaseModel):
    portfolio: Portfolio
    target_allocation: TargetAllocation


class TLHRequest(BaseModel):
    tax_lots: list[dict]
    transaction_history: Optional[list[dict]] = []
    min_loss_threshold: float = 100.0


class SagaStepEvent(BaseModel):
    step_name: str
    status: str
    message: str
    timestamp: str
    is_pivot: bool = False


class SagaStatusResponse(BaseModel):
    transaction_id: str
    status: str
    steps_completed: int
    total_steps: int
    current_step: Optional[str] = None
    logs: list[dict] = []
    error: Optional[str] = None


# =============================================================================
# In-Memory Storage (Demo - use database in production)
# =============================================================================

class SagaStore:
    """In-memory store for saga execution state."""
    
    def __init__(self):
        self.sagas: dict[str, dict] = {}
        self.connections: dict[str, list[WebSocket]] = {}
    
    def create_saga(self, transaction_id: str, saga_type: str, total_steps: int):
        self.sagas[transaction_id] = {
            "transaction_id": transaction_id,
            "saga_type": saga_type,
            "status": "pending",
            "steps_completed": 0,
            "total_steps": total_steps,
            "current_step": None,
            "logs": [],
            "error": None,
            "created_at": datetime.now().isoformat(),
        }
    
    def update_saga(self, transaction_id: str, **kwargs):
        if transaction_id in self.sagas:
            self.sagas[transaction_id].update(kwargs)
    
    def add_log(self, transaction_id: str, log: dict):
        if transaction_id in self.sagas:
            self.sagas[transaction_id]["logs"].append(log)
    
    def get_saga(self, transaction_id: str) -> Optional[dict]:
        return self.sagas.get(transaction_id)
    
    async def broadcast(self, transaction_id: str, message: dict):
        """Broadcast message to all WebSocket connections for this saga."""
        if transaction_id in self.connections:
            for ws in self.connections[transaction_id]:
                try:
                    await ws.send_json(message)
                except:
                    pass


saga_store = SagaStore()


# =============================================================================
# Default Portfolio (Demo)
# =============================================================================

DEFAULT_PORTFOLIO = {
    "holdings": [
        {"asset": "AAPL", "class": "stocks", "value": 25000},
        {"asset": "MSFT", "class": "stocks", "value": 20000},
        {"asset": "GOOGL", "class": "stocks", "value": 15000},
        {"asset": "BND", "class": "bonds", "value": 20000},
        {"asset": "TLT", "class": "bonds", "value": 10000},
        {"asset": "CASH", "class": "cash", "value": 8000},
        {"asset": "GLD", "class": "alternatives", "value": 2000},
    ],
    "total_value": 100000,
}


# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("🚀 CyborgAdvisor API starting...")
    yield
    print("👋 CyborgAdvisor API shutting down...")


app = FastAPI(
    title="CyborgAdvisor API",
    description="Neurosymbolic Portfolio Rebalancer with Saga Pattern",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Portfolio Endpoints
# =============================================================================

@app.get("/api/v1/portfolio")
async def get_portfolio():
    """Get current portfolio data."""
    return DEFAULT_PORTFOLIO


@app.post("/api/v1/portfolio")
async def update_portfolio(portfolio: Portfolio):
    """Update portfolio data."""
    # In production: save to database
    return {"status": "success", "portfolio": portfolio.dict()}


# =============================================================================
# Rebalance Saga Endpoints
# =============================================================================

@app.post("/api/v1/rebalance/execute")
async def execute_rebalance(request: RebalanceRequest):
    """
    Execute portfolio rebalancing via Saga pattern.
    
    Returns transaction ID for tracking.
    """
    # Convert request to saga context
    portfolio_data = {
        "holdings": [h.dict() for h in request.portfolio.holdings],
        "total_value": request.portfolio.total_value,
    }
    
    target_allocation = request.target_allocation.dict()
    
    # Calculate proposed trades (simplified)
    from src.nodes.financial_calculator import calculate_rebalance
    try:
        trades = calculate_rebalance(portfolio_data, target_allocation)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create saga context
    ctx: SagaContext = {
        "transaction_id": "",
        "portfolio_data": portfolio_data,
        "proposed_trades": [dict(t) for t in trades],
        "executed_steps": [],
        "logs": [],
        "error": None,
    }
    
    # Execute saga
    saga = RebalanceSaga()
    result = saga.run(ctx)
    
    return {
        "transaction_id": result.transaction_id,
        "status": result.status.value,
        "trades": trades,
        "logs": [log.to_dict() for log in result.logs],
        "error": result.error,
    }


@app.get("/api/v1/rebalance/preview")
async def preview_rebalance(
    stocks: float = 0.6,
    bonds: float = 0.3,
    cash: float = 0.05,
    alternatives: float = 0.05,
):
    """Preview rebalancing trades without executing."""
    from src.nodes.financial_calculator import calculate_rebalance
    
    target_allocation = {
        "stocks": stocks,
        "bonds": bonds,
        "cash": cash,
        "alternatives": alternatives,
    }
    
    try:
        trades = calculate_rebalance(DEFAULT_PORTFOLIO, target_allocation)
        return {
            "trades": [dict(t) for t in trades],
            "target_allocation": target_allocation,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Tax Loss Harvesting Endpoints
# =============================================================================

def _generate_mock_tax_lots() -> list[dict]:
    """Generate 28 realistic tax lot entries (standalone version)."""
    from datetime import timedelta
    base_date = datetime.now()
    
    mock_data = [
        ("AAPL", 185.50, 172.30, 50, base_date - timedelta(days=45)),
        ("AAPL", 192.00, 172.30, 30, base_date - timedelta(days=120)),
        ("MSFT", 420.00, 385.50, 25, base_date - timedelta(days=200)),
        ("GOOGL", 155.00, 138.20, 40, base_date - timedelta(days=90)),
        ("NVDA", 890.00, 750.00, 15, base_date - timedelta(days=60)),
        ("META", 520.00, 485.00, 20, base_date - timedelta(days=180)),
        ("VTI", 265.00, 248.50, 100, base_date - timedelta(days=400)),
        ("VOO", 480.00, 455.00, 50, base_date - timedelta(days=450)),
        ("BND", 78.00, 72.50, 200, base_date - timedelta(days=500)),
        ("VXUS", 62.00, 55.80, 150, base_date - timedelta(days=380)),
        ("GLD", 195.00, 182.00, 60, base_date - timedelta(days=100)),
        ("AAPL", 125.00, 172.30, 100, base_date - timedelta(days=800)),
        ("MSFT", 280.00, 385.50, 50, base_date - timedelta(days=900)),
        ("GOOGL", 95.00, 138.20, 80, base_date - timedelta(days=750)),
        ("AMZN", 145.00, 185.50, 45, base_date - timedelta(days=600)),
        ("VTI", 195.00, 248.50, 200, base_date - timedelta(days=1100)),
        ("VOO", 350.00, 455.00, 75, base_date - timedelta(days=950)),
        ("TSLA", 265.00, 248.00, 35, base_date - timedelta(days=150)),
        ("TSLA", 180.00, 248.00, 25, base_date - timedelta(days=420)),
        ("SPY", 485.00, 472.00, 40, base_date - timedelta(days=80)),
        ("IVV", 520.00, 505.00, 30, base_date - timedelta(days=95)),
        ("AGG", 105.00, 98.50, 150, base_date - timedelta(days=300)),
        ("VNQ", 95.00, 88.00, 80, base_date - timedelta(days=250)),
        ("SCHB", 58.00, 54.50, 120, base_date - timedelta(days=180)),
        ("IXUS", 72.00, 65.50, 90, base_date - timedelta(days=220)),
        ("IAU", 42.00, 39.50, 100, base_date - timedelta(days=130)),
        ("SCHZ", 52.00, 48.80, 180, base_date - timedelta(days=280)),
        ("IYR", 102.00, 96.00, 55, base_date - timedelta(days=190)),
    ]
    
    tax_lots = []
    for i, (asset, purchase_price, current_price, quantity, purchase_date) in enumerate(mock_data):
        lot_id = f"LOT_{asset}_{i+1:03d}"
        cost_basis = purchase_price * quantity
        current_value = current_price * quantity
        unrealized_gain_loss = current_value - cost_basis
        days_held = (base_date - purchase_date).days
        holding_period = "long_term" if days_held >= 365 else "short_term"
        
        tax_lots.append({
            "lot_id": lot_id,
            "asset": asset,
            "purchase_date": purchase_date.isoformat(),
            "purchase_price": purchase_price,
            "quantity": quantity,
            "current_price": current_price,
            "cost_basis": round(cost_basis, 2),
            "current_value": round(current_value, 2),
            "unrealized_gain_loss": round(unrealized_gain_loss, 2),
            "holding_period": holding_period,
            "days_held": days_held,
        })
    
    return tax_lots


def _identify_loss_opportunities(tax_lots: list[dict], min_threshold: float = 100.0) -> list[dict]:
    """Identify loss opportunities using FIFO ordering."""
    losses = [lot for lot in tax_lots if lot.get("unrealized_gain_loss", 0) < -min_threshold]
    losses.sort(key=lambda x: x.get("unrealized_gain_loss", 0))
    return losses[:10]


def _calculate_tax_impact(losses: list[dict]) -> dict:
    """Calculate estimated tax savings."""
    short_term_losses = sum(abs(lot.get("unrealized_gain_loss", 0)) for lot in losses if lot.get("holding_period") == "short_term")
    long_term_losses = sum(abs(lot.get("unrealized_gain_loss", 0)) for lot in losses if lot.get("holding_period") == "long_term")
    
    return {
        "short_term_losses": round(short_term_losses, 2),
        "long_term_losses": round(long_term_losses, 2),
        "total_losses": round(short_term_losses + long_term_losses, 2),
        "estimated_short_term_savings": round(short_term_losses * 0.29, 2),
        "estimated_long_term_savings": round(long_term_losses * 0.15, 2),
        "total_estimated_savings": round(short_term_losses * 0.29 + long_term_losses * 0.15, 2),
    }


@app.post("/api/v1/tax-loss-harvest/execute")
async def execute_tlh(request: TLHRequest):
    """
    Execute Tax Loss Harvesting via Saga pattern.
    
    Returns transaction ID for tracking.
    """
    # Create saga context
    ctx: SagaContext = {
        "transaction_id": "",
        "portfolio_data": {},
        "proposed_trades": [],
        "executed_steps": [],
        "logs": [],
        "error": None,
        "tax_lots": request.tax_lots,
        "transaction_history": request.transaction_history,
    }
    
    # Create and run saga
    saga = TaxLossHarvestingSaga(min_loss_threshold=request.min_loss_threshold)
    
    # Store saga info
    transaction_id = f"tlh_{datetime.now().timestamp()}"
    saga_store.create_saga(transaction_id, "tlh", 5)
    
    result = saga.run(ctx)
    
    # Update final status
    saga_store.update_saga(
        transaction_id,
        status=result.status.value,
        error=result.error,
    )
    
    return {
        "transaction_id": result.transaction_id,
        "status": result.status.value,
        "summary": result.context.get("tlh_summary"),
        "opportunities": result.context.get("tlh_opportunities"),
        "tax_records": result.context.get("tlh_tax_records"),
        "wash_sale_violations": result.context.get("tlh_wash_sale_violations"),
        "logs": [log.to_dict() for log in result.logs],
        "error": result.error,
    }


@app.get("/api/v1/tax-loss-harvest/opportunities")
async def get_tlh_opportunities(min_threshold: float = 100.0):
    """
    Scan for tax-loss harvesting opportunities.
    
    Returns list of positions with unrealized losses.
    """
    tax_lots = _generate_mock_tax_lots()
    opportunities = _identify_loss_opportunities(tax_lots, min_threshold)
    tax_impact = _calculate_tax_impact(opportunities)
    
    return {
        "total_lots": len(tax_lots),
        "opportunities": opportunities,
        "tax_impact": tax_impact,
    }


@app.get("/api/v1/tax-loss-harvest/wash-sale-check")
async def check_wash_sale(asset: str):
    """
    Check if an asset would trigger wash sale violations.
    """
    # Get fund family info
    family_info = FUND_FAMILY_MAPPING.get(asset, {})
    replacements = get_replacement_suggestions(asset)
    
    return {
        "asset": asset,
        "fund_family": family_info.get("family"),
        "provider": family_info.get("provider"),
        "replacement_suggestions": replacements,
        "substantially_identical_with": [
            ticker for ticker in FUND_FAMILY_MAPPING.keys()
            if ticker != asset and is_substantially_identical(asset, ticker)
        ],
    }


# =============================================================================
# Saga Status Endpoints
# =============================================================================

@app.get("/api/v1/saga/{transaction_id}/status")
async def get_saga_status(transaction_id: str):
    """Get current status of a saga execution."""
    saga = saga_store.get_saga(transaction_id)
    if not saga:
        raise HTTPException(status_code=404, detail="Saga not found")
    return saga


@app.websocket("/api/v1/saga/{transaction_id}/ws")
async def saga_websocket(websocket: WebSocket, transaction_id: str):
    """WebSocket endpoint for real-time saga updates."""
    await websocket.accept()
    
    # Register connection
    if transaction_id not in saga_store.connections:
        saga_store.connections[transaction_id] = []
    saga_store.connections[transaction_id].append(websocket)
    
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Echo back status
            saga = saga_store.get_saga(transaction_id)
            if saga:
                await websocket.send_json(saga)
    except WebSocketDisconnect:
        saga_store.connections[transaction_id].remove(websocket)


async def saga_event_generator(transaction_id: str):
    """Generator for Server-Sent Events."""
    while True:
        saga = saga_store.get_saga(transaction_id)
        if saga:
            yield f"data: {json.dumps(saga)}\n\n"
            if saga["status"] in ["success", "failed", "rolled_back"]:
                break
        await asyncio.sleep(0.5)


@app.get("/api/v1/saga/{transaction_id}/stream")
async def saga_stream(transaction_id: str):
    """Server-Sent Events endpoint for saga status streaming."""
    return StreamingResponse(
        saga_event_generator(transaction_id),
        media_type="text/event-stream",
    )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CyborgAdvisor API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "🤖 CyborgAdvisor API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
