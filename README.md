# Micro-Cap Watchlist & Daily Analysis

Automates a daily pull of prices/volume/market info for **micro-cap** stocks from a watch list, saves CSVs to the repo, and runs a lightweight rules-based analysis to suggest **buys/sells/holds**. On weekends, it runs a deeper scan to rethink the portfolio and hunt for new ideas.

> **Disclaimer:** This is for educational purposes only, not financial advice.

---

## Quick Start (Local)

1. **Install Python 3.10+** and run:
   ```bash
   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Edit your watchlist** in `data/watchlist.csv` (one ticker per row).
3. **Run daily fetch + analysis:**
   ```bash
   python scripts/fetch_prices.py
   python scripts/analyze_portfolio.py --mode daily
   ```
4. **Weekend deep dive:**
   ```bash
   python scripts/analyze_portfolio.py --mode weekend
   ```

CSV outputs will appear in `outputs/daily/` and Markdown reports in `outputs/reports/`.

---

## GitHub Actions (Auto-Run in the Cloud)

This repo includes two workflows in `.github/workflows/`:

- `daily_data.yml`: Runs **each trading weekday** to pull data and generate a daily report.
- `weekend_deep_dive.yml`: Runs on **Saturdays** for a deeper portfolio rethink.

> No PAT needed; uses `GITHUB_TOKEN`. Ensure workflows are **enabled** in your repo settings.

### Adjusting schedules
Update the `cron:` in each workflow (UTC). For example, 22:00 UTC ≈ 18:00 ET (during DST).

---

## Files

- `data/watchlist.csv`: Your tickers. Example included.
- `scripts/fetch_prices.py`: Pulls latest price, volume, market cap & basics via `yfinance`.
- `scripts/analyze_portfolio.py`: Signals + rankings (RSI, 20/50 SMA, volume spike, micro-cap cap filter).
- `outputs/`: CSVs and Markdown reports.
- `.github/workflows/`: CI schedules for daily & weekend jobs.

---

## Strategy (Simple, Transparent Rules)

**Universe:** Your watch list filtered to *micro-caps* (default `< $300M` market cap).
**Signals:**  
- **Trend:** 20D SMA vs 50D SMA (+1 if 20D > 50D)  
- **Momentum:** 5D return (+1 if > 2%)  
- **RSI (14):** +1 if 30 < RSI < 70; +2 if 30 < RSI < 60 (momentum w/ headroom)  
- **Volume Spike:** +1 if today volume > 1.5× 20D average  
- **Quality Gate (data sanity):** non-null market cap, price > $0.20, avg vol > 10k

**Buy candidates:** score ≥ 3, micro-cap, and no hard sell flags.  
**Sell candidates:** 10% trailing drawdown from recent 10D high **or** score ≤ 0 **or** RSI > 75.  
**Hold:** everything else.

You can tune thresholds in `analyze_portfolio.py`.

---

## Notes
- `yfinance` scrapes Yahoo and can rate-limit; keep watch lists modest or add sleeps.
- For a larger universe (screeners, fundamentals), consider Polygon/Alpaca/Alpha Vantage (add your keys).

