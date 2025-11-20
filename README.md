# -dify-
My personal Dify workflow trigger page

## Market snapshot fallback helper

`market_snapshot_fallback.py` fetches the A-share snapshot with an Eastmoney ➜ Sina
fallback chain. It normalizes the columns and reapplies the same price/liquidity
filters you are already using, so you can drop it into your workflow when
`stock_zh_a_spot_em` gets throttled.

Run it standalone to verify connectivity:

```bash
python market_snapshot_fallback.py
```

Or import the helper inside your trading script:

```python
from market_snapshot_fallback import fetch_snapshot_with_fallback

snapshot, logs, provider = fetch_snapshot_with_fallback(capital=3000, top_n=150)
print(f"used provider: {provider}")
print(snapshot.head())
```
