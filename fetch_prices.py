#!/usr/bin/env python
import os, time, sys, argparse
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "daily")

def load_watchlist(path):
    df = pd.read_csv(path)
    df["ticker"] = df["ticker"].str.upper().str.strip()
    df = df.dropna(subset=["ticker"]).drop_duplicates(subset=["ticker"])
    return df

def fetch_snapshot(tickers):
    # Use yfinance fast_info + info fallback
    out = []
    tickers = [t for t in tickers if isinstance(t, str) and len(t) > 0]
    if not tickers:
        return pd.DataFrame(columns=["ticker","price","volume","marketCap","previousClose","open","dayHigh","dayLow","currency","exchange"])
    yf_tickers = yf.Tickers(" ".join(tickers))
    for t in tickers:
        try:
            tk = yf_tickers.tickers.get(t)
            if tk is None:
                continue
            fast = getattr(tk, "fast_info", None) or {}
            info = getattr(tk, "info", {}) or {}
            price = fast.get("last_price") or info.get("regularMarketPrice")
            volume = fast.get("last_volume") or info.get("volume")
            market_cap = fast.get("market_cap") or info.get("marketCap")
            prev_close = fast.get("previous_close") or info.get("previousClose")
            openp = fast.get("open") or info.get("open")
            day_high = fast.get("day_high") or info.get("dayHigh")
            day_low = fast.get("day_low") or info.get("dayLow")
            currency = fast.get("currency") or info.get("currency")
            exchange = info.get("exchange") or info.get("fullExchangeName")

            out.append({
                "ticker": t,
                "price": price,
                "volume": volume,
                "marketCap": market_cap,
                "previousClose": prev_close,
                "open": openp,
                "dayHigh": day_high,
                "dayLow": day_low,
                "currency": currency,
                "exchange": exchange
            })
            time.sleep(0.1)  # be polite
        except Exception as e:
            out.append({"ticker": t, "error": str(e)})
    return pd.DataFrame(out)

def fetch_history(tickers, period="90d", interval="1d"):
    df_all = []
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=period, interval=interval, auto_adjust=False)
            hist = hist.reset_index().rename(columns=str.lower)
            hist["ticker"] = t
            df_all.append(hist[["date","ticker","open","high","low","close","volume"]])
            time.sleep(0.1)
        except Exception as e:
            pass
    if df_all:
        return pd.concat(df_all, ignore_index=True)
    return pd.DataFrame(columns=["date","ticker","open","high","low","close","volume"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", default=os.path.join(DATA_DIR, "watchlist.csv"))
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    wl = load_watchlist(args.watchlist)
    tickers = wl["ticker"].tolist()

    snap = fetch_snapshot(tickers)
    # enrich with notes
    snap = snap.merge(wl, on="ticker", how="left")
    snap["asOf"] = pd.Timestamp.utcnow().tz_localize("UTC")

    # Save today's snapshot
    datestr = pd.Timestamp.now(tz="US/Eastern").strftime("%Y-%m-%d")
    out_csv = os.path.join(OUT_DIR, f"{datestr}_watchlist_snapshot.csv")
    snap.to_csv(out_csv, index=False)

    # Also keep/refresh last snapshot for analysis convenience
    latest_csv = os.path.join(OUT_DIR, "latest_watchlist_snapshot.csv")
    snap.to_csv(latest_csv, index=False)

    # Save recent history for indicators
    hist = fetch_history(tickers, period="180d", interval="1d")
    hist_out = os.path.join(OUT_DIR, f"{datestr}_watchlist_history.csv")
    hist.to_csv(hist_out, index=False)
    hist_latest = os.path.join(OUT_DIR, "latest_watchlist_history.csv")
    hist.to_csv(hist_latest, index=False)

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {hist_out}")

if __name__ == "__main__":
    sys.exit(main())
