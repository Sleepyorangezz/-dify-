"""
Utility to fetch an A-share intraday snapshot with a graceful fallback provider.

When Eastmoney blocks high-volume requests (``stock_zh_a_spot_em``), this helper
tries a secondary source (Sina's snapshot API used by ``stock_zh_a_spot``) so the
rest of the trading pipeline can still receive a ranked stock pool.  The
returned DataFrame is normalized to a common schema so downstream code can apply
filters without worrying about provider-specific column names.
"""
from __future__ import annotations

import time
from typing import Callable, Dict, Iterable, List, Tuple

import akshare as ak
import pandas as pd

ProviderFetcher = Callable[[], pd.DataFrame]


def _standardize_snapshot(raw: pd.DataFrame, provider: str) -> pd.DataFrame:
    """Normalize snapshot columns across Eastmoney and Sina providers."""
    raw = raw.copy()

    if provider == "eastmoney":
        rename_map: Dict[str, str] = {
            "代码": "code",
            "名称": "name",
            "最新价": "price",
            "涨跌幅": "pct_chg",
            "成交额": "amount",
            "换手率": "turnover",
            "流通市值": "mkt_cap",
        }
    else:  # provider == "sina"
        rename_map = {
            "code": "code",
            "name": "name",
            "trade": "price",
            "changepercent": "pct_chg",
            "amount": "amount",
            "turnoverratio": "turnover",
            "nmc": "mkt_cap",
        }

    standardized = raw.rename(columns=rename_map)

    # Ensure required columns exist even if the provider does not return them.
    for col in ("code", "name", "price", "pct_chg", "amount", "turnover", "mkt_cap"):
        if col not in standardized:
            standardized[col] = pd.NA

    return standardized[["code", "name", "price", "pct_chg", "amount", "turnover", "mkt_cap"]]


def _apply_filters(
    df: pd.DataFrame,
    max_price: float,
    top_n: int,
    max_mkt_cap: float = 2000 * 100_000_000,
    turnover_min: float = 3.0,
    turnover_max: float = 25.0,
    pct_chg_floor: float = -3.0,
) -> pd.DataFrame:
    """Apply liquidity, valuation, and momentum filters."""
    df = df.copy()

    df = df[df["price"].notna() & (df["price"] > 0)]
    df = df[~df["name"].str.contains("ST|退", na=False)]
    df = df[df["price"] <= max_price]

    # Normalize numeric columns for downstream filters.
    for col in ("amount", "turnover", "pct_chg", "mkt_cap"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(by="amount", ascending=False).head(top_n)

    if df["mkt_cap"].notna().any():
        df = df[df["mkt_cap"] < max_mkt_cap]

    if df["turnover"].notna().any():
        df = df[(df["turnover"] > turnover_min) & (df["turnover"] < turnover_max)]

    if df["pct_chg"].notna().any():
        df = df[df["pct_chg"] > pct_chg_floor]

    return df


def fetch_snapshot_with_fallback(
    capital: float = 3000,
    top_n: int = 150,
    retries: int = 2,
    sleep_seconds: int = 5,
) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Fetch a filtered intraday snapshot using multiple providers.

    Returns a tuple of (filtered_dataframe, error_messages, provider_name).
    """
    max_price = capital / 100 * 0.95

    providers: Iterable[Tuple[str, ProviderFetcher]] = (
        ("eastmoney", ak.stock_zh_a_spot_em),
        ("sina", ak.stock_zh_a_spot),
    )

    errors: List[str] = []

    for provider_name, fetcher in providers:
        for attempt in range(1, retries + 1):
            try:
                raw = fetcher()
                snapshot = _standardize_snapshot(raw, provider_name)
                filtered = _apply_filters(snapshot, max_price=max_price, top_n=top_n)
                if not filtered.empty:
                    filtered.loc[:, "provider"] = provider_name
                    return filtered, errors, provider_name
            except Exception as exc:  # pragma: no cover - network-dependent
                errors.append(
                    f"{provider_name} attempt {attempt}/{retries} failed: {exc}"
                )
                if attempt < retries:
                    time.sleep(sleep_seconds)

    raise RuntimeError(
        "All providers failed. Errors: " + "; ".join(errors)
    )


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    try:
        result, error_log, provider = fetch_snapshot_with_fallback()
        if error_log:
            print("Warnings during fetch:")
            for msg in error_log:
                print(f" - {msg}")

        print(f"\nUsed provider: {provider}")
        print(result.head())
    except Exception as exc:  # noqa: BLE001
        print(f"Snapshot fetch failed: {exc}")
