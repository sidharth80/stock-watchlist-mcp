# Stock Watchlist MCP

An MCP (Model Context Protocol) server that gives Claude live access to Yahoo Finance data, a personal stock watchlist, and a Prefab UI portfolio dashboard — no API key required.

## Tools

| Tool | Description |
|------|-------------|
| `fetch_stock_data` | Fetch live prices, P/E ratios, analyst ratings, price targets, 52-week ranges, and 5-day history for any ticker |
| `manage_watchlist` | Add, update, remove, and list stocks in your personal watchlist with custom notes |
| `render_portfolio_dashboard` | Generate and open a browser dashboard with stock cards, sparklines, rating badges, and a searchable data table |

## Setup

```bash
# Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the MCP server
python server.py
```

## Stack

- [FastMCP](https://github.com/jlowin/fastmcp) — MCP server framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data (no API key)
- [Prefab UI](https://prefab-ui.com) — declarative dashboard components
