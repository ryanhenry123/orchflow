"""Registered step functions shared by all example runners."""

from src.models.roles import Role
from src.registerfuncs import register
from src.registry import Context

_MOCK_PRICES: dict[str, list[float]] = {
    "AAPL": [150.0, 151.2, 149.8, 152.0],
    "MSFT": [410.5, 412.0, 409.25, 411.75],
}


@register("load_symbol", Role.CALLER)
def load_symbol(ctx: Context) -> str:
    symbol = str(ctx.data.get("symbol", "AAPL")).upper()
    ctx.data["symbol"] = symbol
    return symbol


@register("fetch_prices", Role.CALLER)
def fetch_prices(ctx: Context) -> list[float]:
    symbol = ctx.data["load_symbol"]
    if symbol not in _MOCK_PRICES:
        raise ValueError(f"No price feed for symbol: {symbol}")
    prices = list(_MOCK_PRICES[symbol])
    ctx.data["prices"] = prices
    return prices


@register("validate_prices", Role.EVAL)
def validate_prices(_ctx: Context, result: object) -> bool:
    return isinstance(result, list) and len(result) > 0


@register("log_fetch_failure", Role.FAILURE)
def log_fetch_failure(ctx: Context, exc: Exception) -> None:
    ctx.data["fetch_error"] = str(exc)


@register("summarize", Role.CALLER)
def summarize(ctx: Context) -> dict[str, float | int]:
    prices = ctx.data["fetch_prices"]
    return {"count": len(prices), "avg": sum(prices) / len(prices)}


@register("format_report", Role.CALLER)
def format_report(ctx: Context) -> str:
    summary = ctx.data["summarize"]
    symbol = ctx.data["load_symbol"]
    avg = summary["avg"]
    count = summary["count"]
    return f"{symbol}: avg={avg:.2f} over {count} ticks"
