"""
Prefab UI dashboard for the Stock Watchlist MCP server.
Reads dashboard_data.json (written by render_portfolio_dashboard tool) and
renders a live portfolio view with cards, sparklines, ratings, and a data table.
"""

from prefab_ui import PrefabApp
from prefab_ui.components import (
    Badge, Card, CardContent, CardHeader, CardTitle,
    Column, Grid, H1, H2, H3, Muted, Row, Separator,
)
from prefab_ui.components.charts import Sparkline
from prefab_ui.components.data_table import DataTable, DataTableColumn
from prefab_ui.components.metric import Metric
import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "dashboard_data.json"

# Load data — written fresh by the MCP tool before each export
if DATA_FILE.exists():
    payload = json.loads(DATA_FILE.read_text())
    stocks = payload.get("stocks", [])
    generated_at = payload.get("generated_at", "")
else:
    stocks = []
    generated_at = ""


def _rating_variant(rec: str) -> str:
    rec = (rec or "").lower()
    if rec in ("strong_buy", "buy"):
        return "success"
    if rec in ("strong_sell", "sell"):
        return "destructive"
    return "warning"


def _rating_label(rec: str) -> str:
    return (rec or "N/A").replace("_", " ").title()


def _trend(change_pct: float):
    return "up" if change_pct >= 0 else "down"


def _sentiment(change_pct: float):
    return "positive" if change_pct >= 0 else "negative"


def _sparkline_variant(change_pct: float) -> str:
    return "success" if change_pct >= 0 else "destructive"


def _fmt_price(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_pe(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.1f}x"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_mcap(v) -> str:
    if not v:
        return "N/A"
    try:
        v = float(v)
        if v >= 1e12:
            return f"${v/1e12:.1f}T"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"
    except (TypeError, ValueError):
        return "N/A"


# Build the Prefab app
with PrefabApp(title="Stock Watchlist Dashboard") as app:
    with Column(css_class="p-6 gap-6 max-w-7xl mx-auto"):

        # Header
        with Row(css_class="items-center justify-between"):
            with Column(css_class="gap-1"):
                H1("Stock Watchlist Dashboard")
                if generated_at:
                    Muted(f"Last updated: {generated_at}  •  {len(stocks)} stocks tracked")
                else:
                    Muted("No data yet — run render_portfolio_dashboard() to populate")

        Separator()

        if not stocks:
            with Card():
                with CardContent(css_class="p-8 text-center"):
                    H3("Watchlist is empty")
                    Muted("Use the MCP tools to add stocks and render this dashboard.")
        else:
            # Stock cards — one per stock
            with Grid(css_class="grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"):
                for s in stocks:
                    ticker = s.get("ticker", "")
                    name = s.get("name", ticker)
                    price = s.get("price", 0) or 0
                    change_pct = s.get("change_pct", 0) or 0
                    recommendation = s.get("recommendation", "none")
                    target_price = s.get("target_price")
                    upside_pct = s.get("upside_pct")
                    pe_ratio = s.get("pe_ratio")
                    history = s.get("history", [])
                    notes = s.get("notes", "")
                    error = s.get("error")

                    with Card():
                        with CardHeader(css_class="pb-2"):
                            with Row(css_class="items-start justify-between"):
                                with Column(css_class="gap-0"):
                                    CardTitle(ticker)
                                    Muted(name[:35] + "…" if len(name) > 35 else name)
                                Badge(
                                    label=_rating_label(recommendation),
                                    variant=_rating_variant(recommendation),
                                )

                        with CardContent(css_class="flex flex-col gap-3"):
                            if error:
                                Muted(f"Error fetching data: {error}")
                            else:
                                # Price metric with trend
                                Metric(
                                    label="Current Price",
                                    value=_fmt_price(price),
                                    delta=_fmt_pct(change_pct),
                                    trend=_trend(change_pct),
                                    trend_sentiment=_sentiment(change_pct),
                                )

                                # 5-day sparkline
                                if history:
                                    Sparkline(
                                        data=history,
                                        variant=_sparkline_variant(change_pct),
                                        fill=True,
                                        height=50,
                                        curve="smooth",
                                        stroke_width=2,
                                    )

                                # Analyst target row
                                with Row(css_class="gap-4 text-sm"):
                                    if target_price:
                                        upside_str = f" ({_fmt_pct(upside_pct)} upside)" if upside_pct is not None else ""
                                        Muted(f"Target: {_fmt_price(target_price)}{upside_str}")
                                    Muted(f"P/E: {_fmt_pe(pe_ratio)}")

                                # User notes
                                if notes:
                                    with Card(css_class="bg-muted/40"):
                                        with CardContent(css_class="py-2 px-3"):
                                            Muted(f'"{notes}"')

            Separator()

            # Full data table
            H2("Full Watchlist")
            DataTable(
                columns=[
                    DataTableColumn(key="ticker", header="Ticker", sortable=True),
                    DataTableColumn(key="name", header="Company", sortable=True),
                    DataTableColumn(key="price", header="Price", sortable=True),
                    DataTableColumn(key="change_pct", header="Change %", sortable=True),
                    DataTableColumn(key="recommendation", header="Rating", sortable=True),
                    DataTableColumn(key="target_price", header="Analyst Target", sortable=True),
                    DataTableColumn(key="upside_pct", header="Upside %", sortable=True),
                    DataTableColumn(key="pe_ratio", header="P/E", sortable=True),
                    DataTableColumn(key="market_cap", header="Mkt Cap", sortable=True),
                    DataTableColumn(key="price_at_add", header="Price When Added"),
                    DataTableColumn(key="added_date", header="Date Added"),
                    DataTableColumn(key="notes", header="Your Notes"),
                ],
                rows=[
                    {
                        "ticker": s.get("ticker", ""),
                        "name": s.get("name", ""),
                        "price": _fmt_price(s.get("price")),
                        "change_pct": _fmt_pct(s.get("change_pct")),
                        "recommendation": _rating_label(s.get("recommendation", "")),
                        "target_price": _fmt_price(s.get("target_price")),
                        "upside_pct": _fmt_pct(s.get("upside_pct")),
                        "pe_ratio": _fmt_pe(s.get("pe_ratio")),
                        "market_cap": _fmt_mcap(s.get("market_cap")),
                        "price_at_add": _fmt_price(s.get("price_at_add")),
                        "added_date": s.get("added_date", ""),
                        "notes": s.get("notes", ""),
                    }
                    for s in stocks
                ],
                search=True,
                paginated=True,
                page_size=20,
            )

(Path(__file__).parent / "dashboard.html").write_text(app.html())
