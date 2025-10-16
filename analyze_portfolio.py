#!/usr/bin/env python
import os, sys, argparse
import pandas as pd
import numpy as np
from datetime import datetime
from ta.momentum import RSIIndicator

BASE = os.path.join(os.path.dirname(__file__), "..")
DAILY_DIR = os.path.join(BASE, "outputs", "daily")
REPORT_DIR = os.path.join(BASE, "outputs", "reports")

MICRO_CAP_MAX = 300_000_000  # $300M threshold (tune as needed)

def load_latest():
    snap = pd.read_csv(os.path.join(DAILY_DIR, "latest_watchlist_snapshot.csv"))
    hist = pd.read_csv(os.path.join(DAILY_DIR, "latest_watchlist_history.csv"))
    # ensure dtypes
    for c in ["price","volume","marketCap","open","dayHigh","dayLow","previousClose"]:
        if c in snap.columns:
            snap[c] = pd.to_numeric(snap[c], errors="coerce")
    hist["date"] = pd.to_datetime(hist["date"])
    return snap, hist

def compute_indicators(hist):
    def by_ticker(g):
        g = g.sort_values("date").copy()
        g["ret_5d"] = g["close"].pct_change(5)
        g["sma20"] = g["close"].rolling(20).mean()
        g["sma50"] = g["close"].rolling(50).mean()
        g["avgvol20"] = g["volume"].rolling(20).mean()
        rsi = RSIIndicator(g["close"], window=14)
        g["rsi14"] = rsi.rsi()
        g["rolling_max_10"] = g["close"].rolling(10).max()
        g["drawdown_10"] = g["close"] / g["rolling_max_10"] - 1.0
        return g
    return hist.groupby("ticker", group_keys=False).apply(by_ticker).reset_index(drop=True)

def score_today(snap, ind):
    latest = ind.sort_values("date").groupby("ticker").tail(1)
    merged = latest.merge(snap[["ticker","price","volume","marketCap"]], on="ticker", how="left")

    # micro-cap filter & basic gates
    merged["is_microcap"] = merged["marketCap"] < MICRO_CAP_MAX
    merged["valid_liquidity"] = merged["avgvol20"] > 10_000
    merged["price_gate"] = merged["close"] > 0.20

    # rules-based scoring
    score = 0
    score += (merged["sma20"] > merged["sma50"]).astype(int)
    score += (merged["ret_5d"] > 0.02).astype(int)
    score += ((merged["rsi14"] > 30) & (merged["rsi14"] < 70)).astype(int)
    score += ((merged["volume"] > 1.5 * merged["avgvol20"])).astype(int)
    score += ((merged["rsi14"] > 30) & (merged["rsi14"] < 60)).astype(int)  # extra headroom point

    merged["score"] = score
    merged["sell_flag"] = (merged["drawdown_10"] <= -0.10) | (merged["score"] <= 0) | (merged["rsi14"] > 75)
    merged["buy_flag"]  = (merged["score"] >= 3) & merged["is_microcap"] & merged["valid_liquidity"] & merged["price_gate"] & (~merged["sell_flag"])

    return merged

def to_report(df, mode):
    dt = pd.Timestamp.now(tz="US/Eastern").strftime("%Y-%m-%d")
    lines = [f"# {mode.title()} Portfolio Report — {dt} (US/Eastern)",
             "",
             "> Educational use only. Not financial advice.",
             ""]

    buys = df.loc[df["buy_flag"]].sort_values("score", ascending=False)
    sells = df.loc[df["sell_flag"]].sort_values("score", ascending=True)
    holds = df.loc[~df["buy_flag"] & ~df["sell_flag"]].sort_values("score", ascending=False)

    def block(title, sub):
        lines.append(f"## {title} ({len(sub)})")
        if sub.empty:
            lines.append("_None_")
            lines.append("")
            return
        cols = ["ticker","score","close","rsi14","sma20","sma50","ret_5d","volume","avgvol20","marketCap"]
        cols = [c for c in cols if c in sub.columns]
        tbl = sub[cols].copy()
        # format
        if "close" in tbl:  tbl["close"] = tbl["close"].map(lambda x: f"${x:,.2f}")
        if "marketCap" in tbl: tbl["marketCap"] = tbl["marketCap"].map(lambda x: f"${x:,.0f}")
        if "ret_5d" in tbl: tbl["ret_5d"] = (sub["ret_5d"]*100).map(lambda x: f"{x:,.1f}%")
        if "rsi14" in tbl: tbl["rsi14"] = tbl["rsi14"].map(lambda x: f"{x:,.1f}")
        if "avgvol20" in tbl: tbl["avgvol20"] = tbl["avgvol20"].map(lambda x: f"{x:,.0f}")
        if "volume" in tbl: tbl["volume"] = tbl["volume"].map(lambda x: f"{x:,.0f}")
        lines.append(tbl.to_markdown(index=False))
        lines.append("")

    block("Buy Candidates", buys)
    block("Sell Candidates", sells)
    block("Holds", holds)

    # weekend extras
    if mode == "weekend":
        lines += [
            "## Weekend Rethink Notes",
            "- Rebalance tilt toward top scores but avoid >10% position per name.",
            "- Replace persistent low-score names unless a known catalyst is near-term.",
            "- Hunt ideas: look for rising volume + 20>50 crossovers in last 10 trading days."
        ]

    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily","weekend"], default="daily")
    args = ap.parse_args()

    os.makedirs(REPORT_DIR, exist_ok=True)

    snap, hist = load_latest()
    ind = compute_indicators(hist)
    scored = score_today(snap, ind)

    # Save the scored dataset for auditability
    dt = pd.Timestamp.now(tz="US/Eastern").strftime("%Y-%m-%d")
    scored_out = os.path.join(DAILY_DIR, f"{dt}_scored.csv")
    scored.to_csv(scored_out, index=False)

    # Markdown report
    report_md = to_report(scored, args.mode)
    if args.mode == "daily":
        out_md = os.path.join(REPORT_DIR, f"{dt}_daily_report.md")
    else:
        out_md = os.path.join(REPORT_DIR, f"{dt}_weekend_report.md")
    with open(out_md, "w") as f:
        f.write(report_md)

    # Also refresh latest pointers
    with open(os.path.join(REPORT_DIR, "latest_report.md"), "w") as f:
        f.write(report_md)

    print(f"Wrote: {scored_out}")
    print(f"Wrote: {out_md}")

if __name__ == "__main__":
    main()
