"""
Indian Stock Analyzer — FastAPI Backend
Endpoints:
  GET /api/stocks/list
  GET /api/stocks/ohlcv?ticker=&period=&interval=
  GET /api/stocks/analysis?ticker=&period=&interval=&sl_method=&atr_mult=
  GET /api/fundamentals?ticker=
  GET /api/market/overview
  GET /api/health
"""

from __future__ import annotations

import math
import os
import time
from typing import Any

import numpy as np
import pandas as pd
import ta
import yfinance as yf
from cachetools import TTLCache, cached
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Indian Stock Analyzer API", version="1.0.0")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://indian-stock-analyzer.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tightened after Vercel URL is known
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── In-memory TTL caches (shared across requests) ─────────────────────────────

_ohlcv_cache: TTLCache = TTLCache(maxsize=100, ttl=300)
_info_cache:  TTLCache = TTLCache(maxsize=100, ttl=600)
_mkt_cache:   TTLCache = TTLCache(maxsize=10,  ttl=60)

# ── Constants ─────────────────────────────────────────────────────────────────

POPULAR_STOCKS = {
    "Reliance Industries":  "RELIANCE.NS",
    "TCS":                  "TCS.NS",
    "Infosys":              "INFY.NS",
    "HDFC Bank":            "HDFCBANK.NS",
    "ICICI Bank":           "ICICIBANK.NS",
    "Bharti Airtel":        "BHARTIARTL.NS",
    "State Bank of India":  "SBIN.NS",
    "Hindustan Unilever":   "HINDUNILVR.NS",
    "ITC":                  "ITC.NS",
    "Kotak Mahindra Bank":  "KOTAKBANK.NS",
    "Larsen & Toubro":      "LT.NS",
    "Asian Paints":         "ASIANPAINT.NS",
    "Axis Bank":            "AXISBANK.NS",
    "Maruti Suzuki":        "MARUTI.NS",
    "Sun Pharma":           "SUNPHARMA.NS",
    "Wipro":                "WIPRO.NS",
    "HCL Technologies":     "HCLTECH.NS",
    "Bajaj Finance":        "BAJFINANCE.NS",
    "Titan Company":        "TITAN.NS",
    "Nestlé India":         "NESTLEIND.NS",
}

INDICES = {
    "Nifty 50":     "^NSEI",
    "Sensex":       "^BSESN",
    "Nifty Bank":   "^NSEBANK",
    "Nifty IT":     "^CNXIT",
    "Nifty Midcap": "NIFTY_MID_SELECT.NS",
}

PERIODS = [
    {"label": "1 Week",   "period": "7d",  "interval": "1d"},
    {"label": "1 Month",  "period": "1mo", "interval": "1d"},
    {"label": "3 Months", "period": "3mo", "interval": "1d"},
    {"label": "6 Months", "period": "6mo", "interval": "1d"},
    {"label": "1 Year",   "period": "1y",  "interval": "1wk"},
    {"label": "2 Years",  "period": "2y",  "interval": "1wk"},
    {"label": "5 Years",  "period": "5y",  "interval": "1mo"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(val: Any) -> Any:
    """Convert NaN/Inf to None for JSON safety."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _row_to_dict(row: pd.Series, date_val) -> dict:
    d: dict = {"date": str(date_val)[:10]}
    for col in ["Open", "High", "Low", "Close", "Volume",
                "SMA20", "SMA50", "SMA200", "EMA20",
                "BB_upper", "BB_lower", "BB_mid",
                "RSI", "MACD", "MACD_signal", "MACD_hist",
                "Stoch_K", "Stoch_D", "ATR", "Vol_SMA20"]:
        key = col.lower().replace(" ", "_")
        d[key] = _safe(row.get(col))
    return d


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker: str, period: str, interval: str) -> pd.DataFrame:
    key = (ticker, period, interval)
    if key in _ohlcv_cache:
        return _ohlcv_cache[key]
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(subset=["Close"], inplace=True)
        _ohlcv_cache[key] = df
        return df
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"yfinance error: {exc}")


def fetch_info(ticker: str) -> dict:
    if ticker in _info_cache:
        return _info_cache[ticker]

    t    = yf.Ticker(ticker)
    info: dict = {}

    # 1 — t.info (may return {} on rate-limited servers)
    for _ in range(2):
        try:
            raw = t.info
            if isinstance(raw, dict) and len(raw) > 5:
                info = dict(raw)
                break
        except Exception:
            pass

    # 2 — fast_info
    try:
        fi = t.fast_info
        fi_map = {
            "marketCap":            "market_cap",
            "fiftyTwoWeekHigh":     "year_high",
            "fiftyTwoWeekLow":      "year_low",
            "sharesOutstanding":    "shares",
            "lastPrice":            "last_price",
            "currency":             "currency",
            "exchange":             "exchange",
            "fiftyDayAverage":      "fifty_day_average",
            "twoHundredDayAverage": "two_hundred_day_average",
            "averageVolume":        "three_month_average_volume",
        }
        for key, attr in fi_map.items():
            if not info.get(key):
                try:
                    val = getattr(fi, attr, None)
                    if val is not None:
                        info[key] = val
                except Exception:
                    pass
    except Exception:
        pass

    def _stmt(df_s: pd.DataFrame | None, *names) -> float | None:
        if df_s is None or df_s.empty:
            return None
        col = df_s.columns[0]
        for n in names:
            if n in df_s.index:
                try:
                    v = df_s.loc[n, col]
                    if pd.notna(v):
                        return float(v)
                except Exception:
                    pass
        return None

    _ni = None

    # 3 — income statement
    try:
        fin = t.income_stmt
        if fin is not None and not fin.empty:
            rev = _stmt(fin, "Total Revenue")
            gp  = _stmt(fin, "Gross Profit")
            op  = _stmt(fin, "Operating Income",
                        "Total Operating Income As Reported")
            ni  = _stmt(fin, "Net Income")
            _ni = ni
            if rev and not info.get("totalRevenue"):
                info["totalRevenue"] = rev
            if rev and gp and not info.get("grossMargins"):
                info["grossMargins"] = gp / rev
            if rev and op and not info.get("operatingMargins"):
                info["operatingMargins"] = op / rev
            if rev and ni and not info.get("profitMargins"):
                info["profitMargins"] = ni / rev
            shares = info.get("sharesOutstanding")
            if ni and shares and shares > 0 and not info.get("trailingEps"):
                info["trailingEps"] = ni / shares
    except Exception:
        pass

    # 4 — balance sheet
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            debt   = _stmt(bs, "Total Debt", "Long Term Debt")
            equity = _stmt(bs, "Stockholders Equity", "Common Stock Equity")
            assets = _stmt(bs, "Total Assets")
            if debt   and not info.get("totalDebt"):
                info["totalDebt"] = debt
            if _ni and equity and equity != 0 and not info.get("returnOnEquity"):
                info["returnOnEquity"] = _ni / equity
            if _ni and assets  and assets  != 0 and not info.get("returnOnAssets"):
                info["returnOnAssets"] = _ni / assets
            lp     = info.get("lastPrice")
            shares = info.get("sharesOutstanding")
            if lp and equity and shares and shares > 0 and not info.get("priceToBook"):
                bvps = equity / shares
                if bvps > 0:
                    info["priceToBook"] = lp / bvps
    except Exception:
        pass

    # 5 — cash flow
    try:
        cf = t.cash_flow
        if cf is not None and not cf.empty:
            ocf = _stmt(cf, "Operating Cash Flow",
                        "Cash Flow From Continuing Operating Activities")
            if ocf and not info.get("operatingCashflow"):
                info["operatingCashflow"] = ocf
    except Exception:
        pass

    # 6 — derived P/E
    lp  = info.get("lastPrice")
    eps = info.get("trailingEps")
    if lp and eps and eps > 0 and not info.get("trailingPE"):
        info["trailingPE"] = lp / eps

    # Data quality marker
    key_fields = ["marketCap", "trailingPE", "totalRevenue", "priceToBook",
                  "trailingEps", "profitMargins"]
    filled = sum(1 for k in key_fields if info.get(k) is not None)
    info["_dataQuality"] = "full" if filled >= 4 else ("partial" if filled >= 2 else "minimal")

    _info_cache[ticker] = info
    return info


# ── Indicators ────────────────────────────────────────────────────────────────

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()
    n     = len(df)

    def w(window: int) -> int:
        return max(2, min(window, n))

    df["SMA20"]  = ta.trend.sma_indicator(close, window=w(20))
    df["SMA50"]  = ta.trend.sma_indicator(close, window=w(50))
    df["SMA200"] = ta.trend.sma_indicator(close, window=w(200))
    df["EMA20"]  = ta.trend.ema_indicator(close, window=w(20))

    bb = ta.volatility.BollingerBands(close, window=w(20), window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_mid"]   = bb.bollinger_mavg()

    df["RSI"] = ta.momentum.rsi(close, window=w(14))

    macd = ta.trend.MACD(close,
                         window_slow=w(26), window_fast=w(12), window_sign=w(9))
    df["MACD"]        = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"]   = macd.macd_diff()

    df["Vol_SMA20"] = ta.trend.sma_indicator(vol, window=w(20))
    df["ATR"]       = ta.volatility.average_true_range(
                          high, low, close, window=w(14))

    stoch = ta.momentum.StochasticOscillator(
                high, low, close, window=w(14), smooth_window=w(3))
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    return df


# ── Technical signals ─────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 3:
        return {}
    last   = df.iloc[-1]
    close  = float(last["Close"])
    result = {}

    def _nan(v) -> bool:
        return v is None or (isinstance(v, float) and math.isnan(v))

    rsi = last.get("RSI")
    if not _nan(rsi):
        rsi = float(rsi)
        if   rsi < 30: result["RSI"] = {"signal": "BUY",  "reason": f"RSI={rsi:.1f} — Oversold"}
        elif rsi > 70: result["RSI"] = {"signal": "SELL", "reason": f"RSI={rsi:.1f} — Overbought"}
        else:          result["RSI"] = {"signal": "HOLD", "reason": f"RSI={rsi:.1f} — Neutral"}

    macd_val = last.get("MACD")
    macd_sig = last.get("MACD_signal")
    if not _nan(macd_val) and not _nan(macd_sig):
        if float(macd_val) > float(macd_sig):
            result["MACD"] = {"signal": "BUY",  "reason": "MACD above signal line"}
        else:
            result["MACD"] = {"signal": "SELL", "reason": "MACD below signal line"}

    sma20  = last.get("SMA20")
    sma50  = last.get("SMA50")
    sma200 = last.get("SMA200")
    if not _nan(sma20) and not _nan(sma50):
        s20, s50 = float(sma20), float(sma50)
        if   close > s20 > s50: result["MA Trend"] = {"signal": "BUY",  "reason": "Price > SMA20 > SMA50"}
        elif close < s20 < s50: result["MA Trend"] = {"signal": "SELL", "reason": "Price < SMA20 < SMA50"}
        else:                   result["MA Trend"] = {"signal": "HOLD", "reason": "Mixed MA alignment"}

    if not _nan(sma50) and not _nan(sma200):
        if float(sma50) > float(sma200):
            result["MA Cross"] = {"signal": "BUY",  "reason": "Golden Cross (SMA50 > SMA200)"}
        else:
            result["MA Cross"] = {"signal": "SELL", "reason": "Death Cross (SMA50 < SMA200)"}

    bb_up = last.get("BB_upper")
    bb_lo = last.get("BB_lower")
    if not _nan(bb_up) and not _nan(bb_lo):
        if   close < float(bb_lo): result["Bollinger"] = {"signal": "BUY",  "reason": "Below lower BB — potential reversal"}
        elif close > float(bb_up): result["Bollinger"] = {"signal": "SELL", "reason": "Above upper BB — potential reversal"}
        else:                      result["Bollinger"] = {"signal": "HOLD", "reason": "Price within Bollinger Bands"}

    return result


# ── Levels (stop loss + targets) ──────────────────────────────────────────────

def calculate_levels(df: pd.DataFrame,
                     method: str = "ATR",
                     atr_mult: float = 1.5) -> dict:
    if df.empty or len(df) < 5:
        return {}

    close   = float(df["Close"].iloc[-1])
    atr_col = df["ATR"].dropna() if "ATR" in df.columns else pd.Series([], dtype=float)
    atr_val = float(atr_col.iloc[-1]) if not atr_col.empty else close * 0.015

    lookback   = min(20, len(df))
    recent     = df.tail(lookback)
    swing_low  = float(recent["Low"].min())
    swing_high = float(recent["High"].max())

    fib_look  = min(60, len(df))
    fib_df    = df.tail(fib_look)
    fib_high  = float(fib_df["High"].max())
    fib_low   = float(fib_df["Low"].min())
    fib_range = fib_high - fib_low

    fib_levels = {
        "0.0%":   round(fib_low, 2),
        "23.6%":  round(fib_low + 0.236 * fib_range, 2),
        "38.2%":  round(fib_low + 0.382 * fib_range, 2),
        "50.0%":  round(fib_low + 0.500 * fib_range, 2),
        "61.8%":  round(fib_low + 0.618 * fib_range, 2),
        "78.6%":  round(fib_low + 0.786 * fib_range, 2),
        "100.0%": round(fib_high, 2),
    }

    if method == "ATR":
        stop_loss = close - atr_mult * atr_val
        risk      = max(close - stop_loss, 0.01)
        targets   = {
            "Target 1 (1:1)": round(close + 1 * risk, 2),
            "Target 2 (1:2)": round(close + 2 * risk, 2),
            "Target 3 (1:3)": round(close + 3 * risk, 2),
        }
    elif method == "Swing High/Low":
        stop_loss = swing_low
        risk      = max(close - stop_loss, atr_val * 0.5)
        targets   = {
            "Target 1 (1:1)":       round(close + risk, 2),
            "Target 2 (1:2)":       round(close + 2 * risk, 2),
            "Target 3 — Resistance": round(swing_high, 2),
        }
    else:  # Fibonacci
        supports = sorted([v for v in fib_levels.values() if v < close], reverse=True)
        resists  = sorted([v for v in fib_levels.values() if v > close])
        stop_loss = supports[0] if supports else close - atr_val * 1.5
        risk      = max(close - stop_loss, 0.01)
        tgt_prices = resists[:3] if len(resists) >= 3 else (
            resists + [round(close + (3 - len(resists)) * risk, 2)])
        fib_inv = {v: k for k, v in fib_levels.items()}
        targets = {}
        for i, tp in enumerate(tgt_prices[:3], 1):
            lbl = fib_inv.get(tp, f"Fib T{i}")
            targets[f"Target {i} — {lbl}"] = round(tp, 2)

    stop_loss = round(stop_loss, 2)
    risk      = round(close - stop_loss, 2)

    return {
        "current":    close,
        "stop_loss":  stop_loss,
        "risk":       risk,
        "risk_pct":   round((risk / close) * 100, 2) if close > 0 else 0,
        "atr":        round(atr_val, 2),
        "method":     method,
        "targets":    targets,
        "fib_levels": fib_levels,
    }


# ── Recommendation ────────────────────────────────────────────────────────────

def calculate_recommendation(df: pd.DataFrame, info: dict) -> dict:
    if df.empty or len(df) < 3:
        return {}

    score     = 0
    max_score = 0
    factors: list[dict] = []
    last  = df.iloc[-1]
    close = float(last["Close"])

    def _add(pts: int, label: str):
        nonlocal score, max_score
        max_score += abs(pts) if pts != 0 else 1
        score     += pts
        tag = "BUY" if pts > 0 else ("SELL" if pts < 0 else "HOLD")
        factors.append({"Factor": label, "Signal": tag, "Points": f"{pts:+d}"})

    def _nan(v) -> bool:
        return v is None or (isinstance(v, float) and math.isnan(v))

    rsi = last.get("RSI")
    if not _nan(rsi):
        rsi = float(rsi)
        if   rsi < 30:  _add(+2, f"RSI Oversold ({rsi:.0f})")
        elif rsi < 45:  _add(+1, f"RSI Mildly Bullish ({rsi:.0f})")
        elif rsi > 70:  _add(-2, f"RSI Overbought ({rsi:.0f})")
        elif rsi > 55:  _add(-1, f"RSI Mildly Bearish ({rsi:.0f})")
        else:           _add( 0, f"RSI Neutral ({rsi:.0f})")

    macd_v = last.get("MACD")
    macd_s = last.get("MACD_signal")
    if not _nan(macd_v) and not _nan(macd_s):
        if float(macd_v) > float(macd_s): _add(+2, "MACD above signal")
        else:                              _add(-2, "MACD below signal")

    sma20  = last.get("SMA20")
    sma50  = last.get("SMA50")
    sma200 = last.get("SMA200")
    if not _nan(sma20) and not _nan(sma50):
        s20, s50 = float(sma20), float(sma50)
        if   close > s20 > s50: _add(+2, "Price > SMA20 > SMA50")
        elif close < s20 < s50: _add(-2, "Price < SMA20 < SMA50")
        else:                   _add( 0, "Mixed MA alignment")

    if not _nan(sma50) and not _nan(sma200):
        if float(sma50) > float(sma200): _add(+1, "Golden Cross (SMA50>200)")
        else:                             _add(-1, "Death Cross (SMA50<200)")

    bb_up = last.get("BB_upper")
    bb_lo = last.get("BB_lower")
    if not _nan(bb_up) and not _nan(bb_lo):
        if   close < float(bb_lo): _add(+1, "Below lower Bollinger Band")
        elif close > float(bb_up): _add(-1, "Above upper Bollinger Band")

    pe = info.get("trailingPE")
    if pe and pe > 0:
        if   pe < 15: _add(+1, f"Attractive P/E ({pe:.1f})")
        elif pe > 50: _add(-1, f"Expensive P/E ({pe:.1f})")

    pb = info.get("priceToBook")
    if pb and pb > 0:
        if   pb < 1: _add(+1, f"P/B below book ({pb:.2f})")
        elif pb > 6: _add(-1, f"High P/B ({pb:.2f})")

    margin = info.get("profitMargins")
    if margin is not None:
        if   margin > 0.15: _add(+1, f"Strong margin ({margin*100:.1f}%)")
        elif margin < 0:    _add(-1, "Negative margin")

    if max_score == 0:
        return {}

    pct = (score / max_score) * 100
    if   pct >= 35:  rec, color = "BUY",  "#00C853"
    elif pct <= -35: rec, color = "SELL", "#FF1744"
    else:            rec, color = "HOLD", "#FFC107"

    return {
        "recommendation": rec,
        "color":          color,
        "score":          score,
        "max_score":      max_score,
        "pct":            round(pct, 1),
        "confidence":     round(min(abs(pct), 100), 1),
        "factors":        factors,
    }


# ── Risk score ────────────────────────────────────────────────────────────────

def calculate_risk_score(df: pd.DataFrame, info: dict) -> dict:
    if df.empty:
        return {}

    risk  = 0
    total = 0
    facts: list[dict] = []

    def _risk(pts: int, label: str, detail: str):
        nonlocal risk, total
        total += 3
        risk  += pts
        lvl = "High" if pts == 3 else ("Medium" if pts == 2 else "Low")
        facts.append({"Factor": label, "Detail": detail, "Risk": lvl})

    beta = info.get("beta")
    if beta is not None:
        b = float(beta)
        if   b > 1.5: _risk(3, "Market Beta", f"β={b:.2f} — high volatility vs index")
        elif b > 1.0: _risk(2, "Market Beta", f"β={b:.2f} — above-market volatility")
        else:         _risk(1, "Market Beta", f"β={b:.2f} — low/defensive")

    if "ATR" in df.columns:
        close   = float(df["Close"].iloc[-1])
        atr_col = df["ATR"].dropna()
        if not atr_col.empty:
            vol_pct = (float(atr_col.iloc[-1]) / close) * 100
            if   vol_pct > 3.0: _risk(3, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")
            elif vol_pct > 1.5: _risk(2, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")
            else:               _risk(1, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")

    debt   = info.get("totalDebt")
    mktcap = info.get("marketCap")
    if debt and mktcap and mktcap > 0:
        ratio = debt / mktcap
        if   ratio > 0.6: _risk(3, "Debt / Mkt Cap", f"{ratio:.2f} — high leverage")
        elif ratio > 0.3: _risk(2, "Debt / Mkt Cap", f"{ratio:.2f} — moderate leverage")
        else:             _risk(1, "Debt / Mkt Cap", f"{ratio:.2f} — low leverage")

    h52 = info.get("fiftyTwoWeekHigh")
    l52 = info.get("fiftyTwoWeekLow")
    if h52 and l52 and h52 != l52 and not df.empty:
        pos = (float(df["Close"].iloc[-1]) - l52) / (h52 - l52)
        if   pos < 0.25: _risk(3, "52W Position", f"{pos*100:.0f}% of range — near lows")
        elif pos > 0.80: _risk(2, "52W Position", f"{pos*100:.0f}% of range — near highs")
        else:            _risk(1, "52W Position", f"{pos*100:.0f}% of range — mid range")

    margin = info.get("profitMargins")
    if margin is not None:
        if   margin < 0:    _risk(3, "Profitability", f"Negative margin ({margin*100:.1f}%)")
        elif margin < 0.05: _risk(2, "Profitability", f"Thin margin ({margin*100:.1f}%)")
        else:               _risk(1, "Profitability", f"Healthy margin ({margin*100:.1f}%)")

    if total == 0:
        return {}

    pct = (risk / total) * 100
    if   pct >= 60: level, color = "HIGH",   "#FF1744"
    elif pct >= 35: level, color = "MEDIUM", "#FFC107"
    else:           level, color = "LOW",    "#00C853"

    return {"level": level, "color": color, "pct": round(pct, 1), "factors": facts}


# ── Alerts ────────────────────────────────────────────────────────────────────

def detect_alerts(df: pd.DataFrame) -> list[dict]:
    alerts: list[dict] = []
    if df.empty or len(df) < 3:
        return alerts

    close  = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    def _up(s1: pd.Series, s2: pd.Series) -> bool:
        if len(s1) < 2 or len(s2) < 2:
            return False
        return float(s1.iloc[-2]) < float(s2.iloc[-2]) and float(s1.iloc[-1]) > float(s2.iloc[-1])

    def _dn(s1: pd.Series, s2: pd.Series) -> bool:
        if len(s1) < 2 or len(s2) < 2:
            return False
        return float(s1.iloc[-2]) > float(s2.iloc[-2]) and float(s1.iloc[-1]) < float(s2.iloc[-1])

    def _a(color: str, title: str, desc: str):
        alerts.append({"color": color, "title": title, "description": desc})

    if "RSI" in df.columns:
        rsi = df["RSI"].dropna()
        th30 = pd.Series([30.0] * len(rsi), index=rsi.index)
        th70 = pd.Series([70.0] * len(rsi), index=rsi.index)
        if _up(rsi, th30): _a("green",  "RSI Oversold Reversal",   "RSI crossed above 30 — potential bullish reversal")
        if _dn(rsi, th70): _a("red",    "RSI Overbought Reversal",  "RSI crossed below 70 — potential bearish reversal")

    if "MACD" in df.columns and "MACD_signal" in df.columns:
        macd = df["MACD"].dropna()
        sig  = df["MACD_signal"].dropna()
        if _up(macd, sig): _a("green", "MACD Bullish Crossover", "MACD crossed above signal line")
        if _dn(macd, sig): _a("red",   "MACD Bearish Crossover", "MACD crossed below signal line")

    if "SMA20" in df.columns:
        sma20 = df["SMA20"].dropna()
        if _up(close.reindex(sma20.index), sma20): _a("green", "Price crossed SMA20 ↑", "Bullish: price above 20-day average")
        if _dn(close.reindex(sma20.index), sma20): _a("red",   "Price crossed SMA20 ↓", "Bearish: price below 20-day average")

    if "SMA50" in df.columns and "SMA200" in df.columns:
        sma50  = df["SMA50"].dropna()
        sma200 = df["SMA200"].dropna()
        idx    = sma50.index.intersection(sma200.index)
        if len(idx) >= 2:
            s50, s200 = sma50.reindex(idx), sma200.reindex(idx)
            if _up(s50, s200): _a("green",  "Golden Cross! SMA50 > SMA200", "Strong long-term bullish signal")
            if _dn(s50, s200): _a("red",    "Death Cross! SMA50 < SMA200",  "Strong long-term bearish signal")

    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        lc = float(close.iloc[-1])
        if lc > float(df["BB_upper"].iloc[-1]): _a("yellow", "Bollinger Upper Breakout",  "Price above upper band — overbought or momentum")
        elif lc < float(df["BB_lower"].iloc[-1]): _a("yellow", "Bollinger Lower Breakdown", "Price below lower band — oversold or downtrend")

    if "Vol_SMA20" in df.columns:
        v_now = float(volume.iloc[-1])
        v_avg = float(df["Vol_SMA20"].iloc[-1])
        if v_avg > 0 and v_now >= 2 * v_avg:
            _a("yellow", "Volume Spike Detected", f"Volume is {v_now/v_avg:.1f}× the 20-day average")

    if not alerts:
        _a("green", "No Active Alerts", "No trend reversal signals detected")

    return alerts


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "ts": int(time.time())}


@app.get("/api/stocks/list")
def stocks_list():
    return {
        "stocks":  [{"name": k, "ticker": v} for k, v in POPULAR_STOCKS.items()],
        "indices": [{"name": k, "symbol": v} for k, v in INDICES.items()],
        "periods": PERIODS,
    }


@app.get("/api/stocks/ohlcv")
def ohlcv(
    ticker:   str = Query(...),
    period:   str = Query("6mo"),
    interval: str = Query("1d"),
):
    df = fetch_ohlcv(ticker, period, interval)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data returned for this ticker/period.")

    df = add_indicators(df)

    last_close  = float(df["Close"].iloc[-1])
    prev_close  = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_close
    day_chg     = last_close - prev_close
    day_chg_pct = (day_chg / prev_close) * 100 if prev_close else 0

    info = fetch_info(ticker)
    currency = info.get("currency", "INR")

    rows = []
    for idx_val, row in df.iterrows():
        rows.append(_row_to_dict(row, idx_val))

    return {
        "ticker":   ticker,
        "period":   period,
        "interval": interval,
        "currency": currency,
        "rows":     rows,
        "meta": {
            "last_close":     _safe(last_close),
            "prev_close":     _safe(prev_close),
            "day_change":     _safe(round(day_chg, 2)),
            "day_change_pct": _safe(round(day_chg_pct, 2)),
            "open":           _safe(float(df["Open"].iloc[-1])),
            "high":           _safe(float(df["High"].iloc[-1])),
            "low":            _safe(float(df["Low"].iloc[-1])),
            "volume":         _safe(int(df["Volume"].iloc[-1])),
            "long_name":      info.get("longName", ticker),
        },
    }


@app.get("/api/stocks/analysis")
def analysis(
    ticker:    str   = Query(...),
    period:    str   = Query("6mo"),
    interval:  str   = Query("1d"),
    sl_method: str   = Query("ATR"),
    atr_mult:  float = Query(1.5),
):
    df   = fetch_ohlcv(ticker, period, interval)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data.")
    df   = add_indicators(df)
    info = fetch_info(ticker)

    levels = calculate_levels(df, method=sl_method, atr_mult=atr_mult)
    signals = generate_signals(df)
    alerts  = detect_alerts(df)
    rec     = calculate_recommendation(df, info)
    risk    = calculate_risk_score(df, info)

    return {
        "levels":         levels,
        "signals":        signals,
        "alerts":         alerts,
        "recommendation": rec,
        "risk":           risk,
    }


@app.get("/api/fundamentals")
def fundamentals(ticker: str = Query(...)):
    info = fetch_info(ticker)

    def _g(k):
        v = info.get(k)
        return _safe(v) if isinstance(v, float) else v

    return {
        "ticker":             ticker,
        "long_name":          _g("longName"),
        "sector":             _g("sector"),
        "industry":           _g("industry"),
        "country":            _g("country"),
        "exchange":           _g("exchange"),
        "currency":           _g("currency"),
        "employees":          _g("fullTimeEmployees"),
        "summary":            _g("longBusinessSummary"),
        "market_cap":         _g("marketCap"),
        "trailing_pe":        _g("trailingPE"),
        "forward_pe":         _g("forwardPE"),
        "price_to_book":      _g("priceToBook"),
        "trailing_eps":       _g("trailingEps"),
        "dividend_yield":     _g("dividendYield"),
        "beta":               _g("beta"),
        "total_revenue":      _g("totalRevenue"),
        "gross_margins":      _g("grossMargins"),
        "operating_margins":  _g("operatingMargins"),
        "profit_margins":     _g("profitMargins"),
        "roe":                _g("returnOnEquity"),
        "roa":                _g("returnOnAssets"),
        "total_debt":         _g("totalDebt"),
        "operating_cashflow": _g("operatingCashflow"),
        "fifty_two_week_high":_g("fiftyTwoWeekHigh"),
        "fifty_two_week_low": _g("fiftyTwoWeekLow"),
        "average_volume":     _g("averageVolume"),
        "data_quality":       info.get("_dataQuality", "minimal"),
    }


@app.get("/api/market/overview")
def market_overview():
    key = "overview"
    if key in _mkt_cache:
        return _mkt_cache[key]

    result = []
    for name, symbol in INDICES.items():
        try:
            df = yf.download(symbol, period="5d", interval="1d",
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.dropna(subset=["Close"], inplace=True)
            if df.empty:
                continue
            price = float(df["Close"].iloc[-1])
            prev  = float(df["Close"].iloc[-2]) if len(df) >= 2 else price
            chg   = price - prev
            result.append({
                "name":       name,
                "symbol":     symbol,
                "price":      round(price, 2),
                "change":     round(chg, 2),
                "change_pct": round((chg / prev) * 100, 2) if prev else 0,
            })
        except Exception:
            pass

    _mkt_cache[key] = {"indices": result}
    return _mkt_cache[key]
