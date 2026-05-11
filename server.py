#!/usr/bin/env python3
"""
Stock Watchlist MCP Server
3 tools: fetch_stock_data (internet), manage_watchlist (CRUD), render_portfolio_dashboard (Prefab UI)
"""

from fastmcp import FastMCP
import yfinance as yf
import json
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

mcp = FastMCP("Stock Watchlist")

BASE_DIR = Path(__file__).parent
WATCHLIST_FILE = BASE_DIR / "watchlist.json"
DASHBOARD_DATA_FILE = BASE_DIR / "dashboard_data.json"
PREFAB_CMD = BASE_DIR / "venv/bin/prefab"
DASHBOARD_PY = BASE_DIR / "dashboard.py"
DASHBOARD_HTML = BASE_DIR / "dashboard.html"


def _read_watchlist() -> list:
    if WATCHLIST_FILE.exists():
        return json.loads(WATCHLIST_FILE.read_text())
    return []


def _write_watchlist(data: list) -> None:
    WATCHLIST_FILE.write_text(json.dumps(data, indent=2))


def _fetch_single(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="5d")
    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    prev_close = info.get("previousClose") or price
    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName", ticker),
        "price": round(price, 2),
        "change_pct": round(change_pct, 2),
        "market_cap": info.get("marketCap"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "pe_ratio": info.get("trailingPE"),
        "recommendation": info.get("recommendationKey", "none"),
        "target_price": info.get("targetMeanPrice"),
        "history": [round(v, 2) for v in hist["Close"].tolist()] if not hist.empty else [],
    }


@mcp.tool()
def fetch_stock_data(tickers: list[str]) -> dict:
    """
    Fetch live stock prices, analyst buy/hold/sell ratings, P/E ratios, price targets,
    and 5-day price history from Yahoo Finance. No API key required.

    Args:
        tickers: List of stock ticker symbols, e.g. ["AAPL", "NVDA", "MSFT"]

    Returns:
        Dict mapping each ticker to its data including price, change %, recommendation,
        target price, P/E ratio, and historical prices for charting.
    """
    results = {}
    for ticker in tickers:
        ticker = ticker.upper()
        try:
            results[ticker] = _fetch_single(ticker)
        except Exception as e:
            results[ticker] = {"ticker": ticker, "error": str(e)}
    return results


@mcp.tool()
def manage_watchlist(
    action: str,
    ticker: str = None,
    notes: str = None,
) -> dict:
    """
    CRUD operations on your personal stock watchlist (stored in watchlist.json).

    Args:
        action: One of "add", "read", "update", "delete", "list"
        ticker: Stock ticker symbol (required for add/read/update/delete)
        notes: Your personal notes about why you're watching this stock

    Returns:
        Result of the operation with current watchlist state.
    """
    watchlist = _read_watchlist()

    if action == "list":
        return {"watchlist": watchlist, "count": len(watchlist)}

    if action == "add":
        if not ticker:
            return {"error": "ticker is required for action='add'"}
        ticker = ticker.upper()
        if any(s["ticker"] == ticker for s in watchlist):
            return {"message": f"{ticker} is already in your watchlist", "existing": next(s for s in watchlist if s["ticker"] == ticker)}
        try:
            data = _fetch_single(ticker)
            price_at_add = data["price"]
            name = data["name"]
        except Exception:
            price_at_add = 0
            name = ticker
        entry = {
            "ticker": ticker,
            "name": name,
            "notes": notes or "",
            "added_date": datetime.now().strftime("%Y-%m-%d"),
            "price_at_add": price_at_add,
        }
        watchlist.append(entry)
        _write_watchlist(watchlist)
        return {"success": True, "added": entry, "watchlist_size": len(watchlist)}

    if action == "read":
        if not ticker:
            return {"error": "ticker is required for action='read'"}
        ticker = ticker.upper()
        entry = next((s for s in watchlist if s["ticker"] == ticker), None)
        return entry if entry else {"error": f"{ticker} not found in watchlist"}

    if action == "update":
        if not ticker:
            return {"error": "ticker is required for action='update'"}
        ticker = ticker.upper()
        for entry in watchlist:
            if entry["ticker"] == ticker:
                if notes is not None:
                    entry["notes"] = notes
                _write_watchlist(watchlist)
                return {"success": True, "updated": entry}
        return {"error": f"{ticker} not found in watchlist"}

    if action == "delete":
        if not ticker:
            return {"error": "ticker is required for action='delete'"}
        ticker = ticker.upper()
        before = len(watchlist)
        watchlist = [s for s in watchlist if s["ticker"] != ticker]
        if len(watchlist) == before:
            return {"error": f"{ticker} not found in watchlist"}
        _write_watchlist(watchlist)
        return {"success": True, "deleted": ticker, "watchlist_size": len(watchlist)}

    return {"error": f"Unknown action '{action}'. Valid actions: add, read, update, delete, list"}


@mcp.tool()
def render_portfolio_dashboard() -> str:
    """
    Generate and open a live portfolio dashboard in your browser using Prefab UI.

    The dashboard shows each watched stock with:
    - Current price and daily % change
    - Analyst buy/hold/sell recommendation (color-coded)
    - Analyst price target and upside %
    - 5-day sparkline chart
    - Full data table with P/E ratios and your personal notes

    The dashboard opens as a self-contained HTML file — no inline MCP rendering needed.
    """
    watchlist = _read_watchlist()
    if not watchlist:
        return (
            "Your watchlist is empty. Add stocks first:\n"
            "  manage_watchlist(action='add', ticker='AAPL', notes='Why you like it')"
        )

    # Fetch live data for every stock in the watchlist
    stocks_data = []
    for item in watchlist:
        ticker = item["ticker"]
        try:
            live = _fetch_single(ticker)
            # Merge watchlist metadata (notes, date added) with live data
            merged = {**item, **live}
            # Compute upside to analyst target
            if live.get("target_price") and live.get("price"):
                upside = ((live["target_price"] - live["price"]) / live["price"]) * 100
                merged["upside_pct"] = round(upside, 1)
            else:
                merged["upside_pct"] = None
            stocks_data.append(merged)
        except Exception as e:
            stocks_data.append({**item, "price": 0, "change_pct": 0, "history": [], "error": str(e)})

    # Write fresh data for dashboard.py to read at export time
    DASHBOARD_DATA_FILE.write_text(json.dumps({
        "stocks": stocks_data,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=2))

    # Export Prefab dashboard to a self-contained HTML file
    result = subprocess.run(
        [str(PREFAB_CMD), "export", str(DASHBOARD_PY), "--output", str(DASHBOARD_HTML)],
        capture_output=True, text=True, cwd=str(BASE_DIR)
    )
    if result.returncode != 0:
        return f"Dashboard export failed:\n{result.stderr}\n{result.stdout}"

    # Open in browser
    webbrowser.open(f"file://{DASHBOARD_HTML}")
    tickers = [s["ticker"] for s in stocks_data]
    return (
        f"Dashboard opened in your browser!\n"
        f"Showing {len(stocks_data)} stocks: {', '.join(tickers)}\n"
        f"File: {DASHBOARD_HTML}"
    )


if __name__ == "__main__":
    mcp.run()
