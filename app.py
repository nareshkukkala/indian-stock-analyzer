import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ta
import warnings
warnings.filterwarnings("ignore")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Indian Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #FF6B35;
        text-align: center;
        padding: 0.5rem 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #888;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1E1E2E;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #FF6B35;
    }
    .positive { color: #00C853; font-weight: bold; }
    .negative { color: #FF1744; font-weight: bold; }
    .neutral  { color: #FFC107; font-weight: bold; }
    .signal-buy  { background: #00C853; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; }
    .signal-sell { background: #FF1744; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; }
    .signal-hold { background: #FFC107; color: black;  padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; }
    .level-card {
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
        margin-bottom: 0.4rem;
    }
    .level-sl   { background: rgba(255,23,68,0.15);  border: 1px solid #FF1744; }
    .level-t1   { background: rgba(0,200,83,0.10);   border: 1px solid #00C853; }
    .level-t2   { background: rgba(0,200,83,0.18);   border: 1px solid #00C853; }
    .level-t3   { background: rgba(0,200,83,0.26);   border: 1px solid #00C853; }
    .level-curr { background: rgba(255,107,53,0.15); border: 1px solid #FF6B35; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
POPULAR_STOCKS = {
    "Reliance Industries":    "RELIANCE.NS",
    "TCS":                    "TCS.NS",
    "Infosys":                "INFY.NS",
    "HDFC Bank":              "HDFCBANK.NS",
    "ICICI Bank":             "ICICIBANK.NS",
    "Bharti Airtel":          "BHARTIARTL.NS",
    "State Bank of India":    "SBIN.NS",
    "Hindustan Unilever":     "HINDUNILVR.NS",
    "ITC":                    "ITC.NS",
    "Kotak Mahindra Bank":    "KOTAKBANK.NS",
    "Larsen & Toubro":        "LT.NS",
    "Asian Paints":           "ASIANPAINT.NS",
    "Axis Bank":              "AXISBANK.NS",
    "Maruti Suzuki":          "MARUTI.NS",
    "Sun Pharma":             "SUNPHARMA.NS",
    "Wipro":                  "WIPRO.NS",
    "HCL Technologies":       "HCLTECH.NS",
    "Bajaj Finance":          "BAJFINANCE.NS",
    "Titan Company":          "TITAN.NS",
    "Nestlé India":           "NESTLEIND.NS",
}

INDICES = {
    "Nifty 50":    "^NSEI",
    "Sensex":      "^BSESN",
    "Nifty Bank":  "^NSEBANK",
    "Nifty IT":    "^CNXIT",
    "Nifty Midcap": "NIFTY_MID_SELECT.NS",
}

PERIODS = {
    "1 Week":   ("7d",  "1d"),
    "1 Month":  ("1mo", "1d"),
    "3 Months": ("3mo", "1d"),
    "6 Months": ("6mo", "1d"),
    "1 Year":   ("1y",  "1wk"),
    "2 Years":  ("2y",  "1wk"),
    "5 Years":  ("5y",  "1mo"),
}

# ── Helper functions ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_stock_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_info(ticker: str) -> dict:
    """
    Build a fundamental-data dict for `ticker` using multiple yfinance endpoints.
    Priority: t.info → fast_info → income_stmt → balance_sheet → cash_flow → derived.
    This multi-source approach ensures data is available even when t.info returns {}.
    """
    try:
        t    = yf.Ticker(ticker)
        info = {}

        # ── 1. t.info (full metadata; may be empty / blocked on some servers) ──
        for _attempt in range(2):
            try:
                raw = t.info
                if isinstance(raw, dict) and len(raw) > 5:
                    info = dict(raw)
                    break
            except Exception:
                pass

        # ── 2. fast_info – lighter endpoint, usually works everywhere ──────────
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

        # Helper to pull a float from a financial-statement DataFrame
        def _stmt(df, *row_names):
            if df is None or df.empty:
                return None
            col = df.columns[0]
            for name in row_names:
                if name in df.index:
                    try:
                        val = df.loc[name, col]
                        if pd.notna(val):
                            return float(val)
                    except Exception:
                        pass
            return None

        # ── 3. Income statement ───────────────────────────────────────────────
        _ni = None
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

        # ── 4. Balance sheet ──────────────────────────────────────────────────
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

                # P/B from book value per share
                lp     = info.get("lastPrice")
                shares = info.get("sharesOutstanding")
                if lp and equity and shares and shares > 0 and not info.get("priceToBook"):
                    bvps = equity / shares
                    if bvps > 0:
                        info["priceToBook"] = lp / bvps
        except Exception:
            pass

        # ── 5. Cash-flow statement ────────────────────────────────────────────
        try:
            cf = t.cash_flow
            if cf is not None and not cf.empty:
                ocf = _stmt(cf, "Operating Cash Flow",
                            "Cash Flow From Continuing Operating Activities")
                if ocf and not info.get("operatingCashflow"):
                    info["operatingCashflow"] = ocf
        except Exception:
            pass

        # ── 6. Derived P/E ────────────────────────────────────────────────────
        lp  = info.get("lastPrice")
        eps = info.get("trailingEps")
        if lp and eps and eps > 0 and not info.get("trailingPE"):
            try:
                info["trailingPE"] = lp / eps
            except Exception:
                pass

        return info
    except Exception:
        return {}


def fmt_currency(val, currency="₹"):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if val >= 1e12:
        return f"{currency}{val/1e12:.2f}T"
    if val >= 1e9:
        return f"{currency}{val/1e9:.2f}B"
    if val >= 1e7:
        return f"{currency}{val/1e7:.2f}Cr"
    if val >= 1e5:
        return f"{currency}{val/1e5:.2f}L"
    return f"{currency}{val:,.2f}"


def fmt_pct(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val*100:.2f}%"


def fmt_num(val, decimals=2):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val:.{decimals}f}"


def color_delta(val):
    if val is None:
        return "neutral"
    return "positive" if val >= 0 else "negative"


# ── Technical Indicators ───────────────────────────────────────────────────────

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()
    n     = len(df)

    def w(window):
        """Cap window to available rows (minimum 2)."""
        return max(2, min(window, n))

    # Moving Averages
    df["SMA20"]  = ta.trend.sma_indicator(close, window=w(20))
    df["SMA50"]  = ta.trend.sma_indicator(close, window=w(50))
    df["SMA200"] = ta.trend.sma_indicator(close, window=w(200))
    df["EMA20"]  = ta.trend.ema_indicator(close, window=w(20))

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=w(20), window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_mid"]   = bb.bollinger_mavg()

    # RSI
    df["RSI"] = ta.momentum.rsi(close, window=w(14))

    # MACD
    macd = ta.trend.MACD(close, window_slow=w(26), window_fast=w(12), window_sign=w(9))
    df["MACD"]        = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"]   = macd.macd_diff()

    # Volume SMA
    df["Vol_SMA20"] = ta.trend.sma_indicator(vol, window=w(20))

    # ATR
    df["ATR"] = ta.volatility.average_true_range(high, low, close, window=w(14))

    # Stochastic
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=w(14), smooth_window=w(3))
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    return df


def generate_signals(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}

    last = df.iloc[-1]
    signals = {}

    # RSI signal
    rsi = last.get("RSI", np.nan)
    if not np.isnan(rsi):
        if rsi < 30:
            signals["RSI"] = ("BUY", f"RSI={rsi:.1f} — Oversold")
        elif rsi > 70:
            signals["RSI"] = ("SELL", f"RSI={rsi:.1f} — Overbought")
        else:
            signals["RSI"] = ("HOLD", f"RSI={rsi:.1f} — Neutral")

    # MACD signal
    macd_val = last.get("MACD", np.nan)
    macd_sig = last.get("MACD_signal", np.nan)
    if not (np.isnan(macd_val) or np.isnan(macd_sig)):
        if macd_val > macd_sig:
            signals["MACD"] = ("BUY", "MACD above signal line")
        else:
            signals["MACD"] = ("SELL", "MACD below signal line")

    # Moving Average signal
    close = last["Close"]
    sma20 = last.get("SMA20", np.nan)
    sma50 = last.get("SMA50", np.nan)
    sma200 = last.get("SMA200", np.nan)
    if not (np.isnan(sma20) or np.isnan(sma50)):
        if close > sma20 > sma50:
            signals["MA Trend"] = ("BUY", "Price > SMA20 > SMA50")
        elif close < sma20 < sma50:
            signals["MA Trend"] = ("SELL", "Price < SMA20 < SMA50")
        else:
            signals["MA Trend"] = ("HOLD", "Mixed MA alignment")

    # Golden/Death cross
    if not (np.isnan(sma50) or np.isnan(sma200)):
        if sma50 > sma200:
            signals["MA Cross"] = ("BUY", "Golden Cross (SMA50 > SMA200)")
        else:
            signals["MA Cross"] = ("SELL", "Death Cross (SMA50 < SMA200)")

    # Bollinger Band signal
    bb_upper = last.get("BB_upper", np.nan)
    bb_lower = last.get("BB_lower", np.nan)
    if not (np.isnan(bb_upper) or np.isnan(bb_lower)):
        if close < bb_lower:
            signals["Bollinger"] = ("BUY", "Price below lower BB — potential reversal")
        elif close > bb_upper:
            signals["Bollinger"] = ("SELL", "Price above upper BB — potential reversal")
        else:
            signals["Bollinger"] = ("HOLD", "Price within Bollinger Bands")

    return signals


# ── Target & Stop Loss Calculator ─────────────────────────────────────────────

def calculate_levels(df: pd.DataFrame, method: str = "ATR", atr_mult_sl: float = 1.5) -> dict:
    """Return stop loss, three targets, Fibonacci levels, and ATR for the latest bar."""
    if df.empty or len(df) < 14:
        return {}

    close   = float(df["Close"].iloc[-1])
    atr_val = float(df["ATR"].iloc[-1]) if ("ATR" in df.columns and not np.isnan(df["ATR"].iloc[-1])) else close * 0.015

    # Swing high/low over last 20 bars
    lookback = min(20, len(df))
    recent   = df.tail(lookback)
    swing_low  = float(recent["Low"].min())
    swing_high = float(recent["High"].max())

    # Fibonacci range over last 60 bars
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
        stop_loss = close - atr_mult_sl * atr_val
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
            "Target 1 (1:1)": round(close + 1 * risk, 2),
            "Target 2 (1:2)": round(close + 2 * risk, 2),
            "Target 3 — Resistance": round(swing_high, 2),
        }

    else:  # Fibonacci
        fib_supports = sorted([v for v in fib_levels.values() if v < close], reverse=True)
        fib_resists  = sorted([v for v in fib_levels.values() if v > close])
        stop_loss    = fib_supports[0] if fib_supports else close - atr_val * 1.5
        risk         = max(close - stop_loss, 0.01)
        tgt_prices   = fib_resists[:3] if len(fib_resists) >= 3 else (fib_resists + [round(close + (3 - len(fib_resists)) * risk, 2)])
        fib_label_map = {v: k for k, v in fib_levels.items()}
        targets = {}
        for i, tp in enumerate(tgt_prices[:3], 1):
            lbl = fib_label_map.get(tp, f"Fib T{i}")
            targets[f"Target {i} — {lbl}"] = round(tp, 2)

    stop_loss = round(stop_loss, 2)
    risk      = round(close - stop_loss, 2)

    return {
        "current":    close,
        "stop_loss":  stop_loss,
        "risk":       risk,
        "risk_pct":   round((risk / close) * 100, 2) if close > 0 else 0,
        "targets":    targets,
        "fib_levels": fib_levels,
        "atr":        round(atr_val, 2),
        "method":     method,
    }


# ── Chart builders ─────────────────────────────────────────────────────────────

def build_price_chart(df: pd.DataFrame, ticker: str, chart_type: str, show_bb: bool, show_ma: bool, levels: dict = None) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} Price", "Volume", "RSI"),
    )

    # Price
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"],  close=df["Close"],
            name="Price",
            increasing_line_color="#00C853",
            decreasing_line_color="#FF1744",
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines", name="Close",
            line=dict(color="#FF6B35", width=2),
        ), row=1, col=1)

    # Moving Averages
    if show_ma:
        ma_colors = {"SMA20": "#00BCD4", "SMA50": "#FFC107", "SMA200": "#E040FB"}
        for ma, color in ma_colors.items():
            if ma in df.columns and df[ma].notna().any():
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[ma],
                    mode="lines", name=ma,
                    line=dict(color=color, width=1.2, dash="dot"),
                ), row=1, col=1)

    # Bollinger Bands
    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"],
            mode="lines", name="BB Upper",
            line=dict(color="rgba(128,128,255,0.5)", width=1),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"],
            mode="lines", name="BB Lower",
            line=dict(color="rgba(128,128,255,0.5)", width=1),
            fill="tonexty", fillcolor="rgba(128,128,255,0.07)",
        ), row=1, col=1)

    # Volume
    colors = ["#00C853" if c >= o else "#FF1744"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume", marker_color=colors, showlegend=False,
    ), row=2, col=1)

    if "Vol_SMA20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Vol_SMA20"],
            mode="lines", name="Vol SMA20",
            line=dict(color="#FFC107", width=1.2),
        ), row=2, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            mode="lines", name="RSI",
            line=dict(color="#FF6B35", width=1.5),
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red",   opacity=0.6, row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.6, row=3, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)", row=3, col=1)

    # Target & Stop Loss horizontal lines
    if levels:
        sl = levels["stop_loss"]
        fig.add_hline(
            y=sl, line_dash="dash", line_color="#FF1744", line_width=1.5,
            annotation_text=f"SL ₹{sl:,.2f}", annotation_position="right",
            annotation_font_color="#FF1744", row=1, col=1,
        )
        tgt_colors = ["#66BB6A", "#00C853", "#1DE9B6"]
        for (label, price), color in zip(levels["targets"].items(), tgt_colors):
            short = label.split(" ")[0] + " " + label.split(" ")[1]
            fig.add_hline(
                y=price, line_dash="dot", line_color=color, line_width=1.5,
                annotation_text=f"{short} ₹{price:,.2f}",
                annotation_position="right",
                annotation_font_color=color, row=1, col=1,
            )

    fig.update_layout(
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=80),
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    if "MACD" not in df.columns:
        return fig

    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"],
        mode="lines", name="MACD",
        line=dict(color="#00BCD4", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_signal"],
        mode="lines", name="Signal",
        line=dict(color="#FF6B35", width=1.5),
    ))
    colors = ["#00C853" if v >= 0 else "#FF1744" for v in df["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACD_hist"],
        name="Histogram", marker_color=colors,
    ))
    fig.add_hline(y=0, line_color="white", opacity=0.3)
    fig.update_layout(
        template="plotly_dark",
        height=300,
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        title="MACD",
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=50, b=20),
    )
    return fig


def build_stoch_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if "Stoch_K" not in df.columns:
        return fig

    fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_K"], mode="lines",
                             name="%K", line=dict(color="#00BCD4", width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_D"], mode="lines",
                             name="%D", line=dict(color="#FF6B35", width=1.5, dash="dot")))
    fig.add_hline(y=80, line_dash="dash", line_color="red",   opacity=0.6)
    fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.6)
    fig.update_layout(
        template="plotly_dark", height=250,
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        title="Stochastic Oscillator",
        yaxis=dict(range=[0, 100]),
        margin=dict(l=40, r=20, t=50, b=20),
    )
    return fig


# ── Target & Stop Loss Display ────────────────────────────────────────────────

def show_target_stop_loss(levels: dict, sym: str = "₹"):
    if not levels:
        st.info("Not enough data to calculate levels.")
        return

    current   = levels["current"]
    stop_loss = levels["stop_loss"]
    risk      = levels["risk"]
    risk_pct  = levels["risk_pct"]
    targets   = levels["targets"]
    method    = levels["method"]
    atr       = levels["atr"]

    st.markdown(f"**Method: {method}** &nbsp;|&nbsp; ATR(14): {sym}{atr:,.2f}")

    # ── Summary cards ─────────────────────────────────────────────────────────
    tgt_list   = list(targets.items())
    ncols      = 1 + len(tgt_list)          # current + SL + targets
    cols       = st.columns(ncols + 1)       # +1 for SL

    with cols[0]:
        st.markdown(
            f"<div class='level-card level-curr'>"
            f"<div style='font-size:0.75rem;color:#aaa;'>Current Price</div>"
            f"<div style='font-size:1.4rem;font-weight:700;color:#FF6B35;'>{sym}{current:,.2f}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            f"<div class='level-card level-sl'>"
            f"<div style='font-size:0.75rem;color:#aaa;'>Stop Loss</div>"
            f"<div style='font-size:1.4rem;font-weight:700;color:#FF1744;'>{sym}{stop_loss:,.2f}</div>"
            f"<div style='font-size:0.8rem;color:#FF1744;'>−{sym}{risk:,.2f} &nbsp; −{risk_pct:.2f}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    tgt_css = ["level-t1", "level-t2", "level-t3"]
    for i, (label, price) in enumerate(tgt_list):
        upside     = price - current
        upside_pct = (upside / current) * 100
        rr         = upside / risk if risk > 0 else 0
        css        = tgt_css[i] if i < len(tgt_css) else "level-t3"
        short_lbl  = label
        with cols[i + 2]:
            st.markdown(
                f"<div class='level-card {css}'>"
                f"<div style='font-size:0.75rem;color:#aaa;'>{short_lbl}</div>"
                f"<div style='font-size:1.4rem;font-weight:700;color:#00C853;'>{sym}{price:,.2f}</div>"
                f"<div style='font-size:0.8rem;color:#00C853;'>+{sym}{upside:,.2f} &nbsp; +{upside_pct:.2f}%</div>"
                f"<div style='font-size:0.75rem;color:#aaa;'>R:R = 1:{rr:.1f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Fibonacci levels table ─────────────────────────────────────────────────
    with st.expander("Fibonacci Retracement Levels"):
        fib_rows = []
        for label, price in levels["fib_levels"].items():
            dist     = price - current
            dist_pct = (dist / current) * 100
            zone     = "Support" if price < current else ("Resistance" if price > current else "Current")
            fib_rows.append({
                "Fib Level": label,
                "Price":     f"{sym}{price:,.2f}",
                "Distance":  f"{dist:+,.2f}",
                "Distance %": f"{dist_pct:+.2f}%",
                "Zone":      zone,
            })
        fib_df = pd.DataFrame(fib_rows)
        st.dataframe(fib_df, use_container_width=True, hide_index=True)

    # ── Position size calculator ───────────────────────────────────────────────
    with st.expander("Position Size Calculator"):
        st.caption("How many shares to buy based on your risk tolerance")
        col_a, col_b, col_c = st.columns(3)
        capital    = col_a.number_input("Total Capital (₹)", value=100000, step=10000, min_value=1000)
        risk_pct_input = col_b.number_input("Risk per trade (%)", value=1.0, step=0.5, min_value=0.1, max_value=10.0)
        entry_price = col_c.number_input("Entry Price (₹)", value=float(current), step=0.5, min_value=0.01)

        risk_amount   = capital * (risk_pct_input / 100)
        sl_distance   = entry_price - stop_loss
        if sl_distance > 0:
            qty           = int(risk_amount / sl_distance)
            invest_amount = qty * entry_price
            max_loss      = qty * sl_distance
            tgt_values    = [(lbl, qty * (p - entry_price)) for lbl, p in targets.items()]

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Quantity",        f"{qty:,} shares")
            r2.metric("Investment",      f"₹{invest_amount:,.0f}")
            r3.metric("Max Loss",        f"₹{max_loss:,.0f}", f"−{risk_pct_input:.1f}% of capital", delta_color="inverse")
            if tgt_values:
                lbl0, profit0 = tgt_values[0]
                r4.metric(f"Profit at {lbl0.split()[0]+' '+lbl0.split()[1]}", f"₹{profit0:,.0f}")

            if len(tgt_values) > 1:
                st.markdown("**Profit at each target:**")
                t_cols = st.columns(len(tgt_values))
                for tc, (lbl, profit) in zip(t_cols, tgt_values):
                    tc.metric(lbl, f"₹{profit:,.0f}")
        else:
            st.warning("Stop loss is above entry price — check your inputs.")


# ── Recommendation Engine ─────────────────────────────────────────────────────

def calculate_recommendation(df: pd.DataFrame, info: dict) -> dict:
    """Score-based Buy / Hold / Sell from technicals + fundamentals."""
    if df.empty or len(df) < 3:
        return {}

    score     = 0
    max_score = 0
    factors   = []
    last      = df.iloc[-1]
    close     = float(last["Close"])

    def _add(points, label, direction):
        nonlocal score, max_score
        abs_pts = abs(points)
        max_score += abs_pts
        score     += points
        tag = "BUY" if points > 0 else ("SELL" if points < 0 else "HOLD")
        factors.append({"Factor": label, "Signal": tag, "Points": f"{points:+d}"})

    # ── Technical ──────────────────────────────────────────────────────────────
    rsi = last.get("RSI", np.nan)
    if not (isinstance(rsi, float) and np.isnan(rsi)):
        rsi = float(rsi)
        if   rsi < 30:  _add(+2, f"RSI Oversold ({rsi:.0f})",    "BUY")
        elif rsi < 45:  _add(+1, f"RSI Mildly Bullish ({rsi:.0f})", "BUY")
        elif rsi > 70:  _add(-2, f"RSI Overbought ({rsi:.0f})",  "SELL")
        elif rsi > 55:  _add(-1, f"RSI Mildly Bearish ({rsi:.0f})", "SELL")
        else:           _add( 0, f"RSI Neutral ({rsi:.0f})",     "HOLD"); max_score += 1

    macd     = last.get("MACD",        np.nan)
    macd_sig = last.get("MACD_signal", np.nan)
    if not any(isinstance(v, float) and np.isnan(v) for v in [macd, macd_sig]):
        if float(macd) > float(macd_sig):
            _add(+2, "MACD above signal", "BUY")
        else:
            _add(-2, "MACD below signal", "SELL")

    sma20  = last.get("SMA20",  np.nan)
    sma50  = last.get("SMA50",  np.nan)
    sma200 = last.get("SMA200", np.nan)
    if not any(isinstance(v, float) and np.isnan(v) for v in [sma20, sma50]):
        sma20, sma50 = float(sma20), float(sma50)
        if   close > sma20 > sma50: _add(+2, "Price > SMA20 > SMA50", "BUY")
        elif close < sma20 < sma50: _add(-2, "Price < SMA20 < SMA50", "SELL")
        else:                       _add( 0, "Mixed MA alignment",     "HOLD"); max_score += 1

    if not any(isinstance(v, float) and np.isnan(v) for v in [sma50, sma200]):
        if float(sma50) > float(sma200): _add(+1, "Golden Cross (SMA50>200)", "BUY")
        else:                             _add(-1, "Death Cross (SMA50<200)",  "SELL")

    bb_upper = last.get("BB_upper", np.nan)
    bb_lower = last.get("BB_lower", np.nan)
    if not any(isinstance(v, float) and np.isnan(v) for v in [bb_upper, bb_lower]):
        if   close < float(bb_lower): _add(+1, "Below lower Bollinger Band", "BUY")
        elif close > float(bb_upper): _add(-1, "Above upper Bollinger Band", "SELL")

    # ── Fundamental ───────────────────────────────────────────────────────────
    pe = info.get("trailingPE")
    if pe and pe > 0:
        if   pe < 15: _add(+1, f"Attractive P/E ({pe:.1f})", "BUY")
        elif pe > 50: _add(-1, f"Expensive P/E ({pe:.1f})",  "SELL")

    pb = info.get("priceToBook")
    if pb and pb > 0:
        if   pb < 1: _add(+1, f"P/B below book ({pb:.2f})", "BUY")
        elif pb > 6: _add(-1, f"High P/B ({pb:.2f})",       "SELL")

    margin = info.get("profitMargins")
    if margin is not None:
        if   margin > 0.15: _add(+1, f"Strong margin ({margin*100:.1f}%)", "BUY")
        elif margin < 0:    _add(-1, "Negative margin",                     "SELL")

    if max_score == 0:
        return {}

    pct = (score / max_score) * 100
    if   pct >= 35:  rec, color = "BUY",  "#00C853"
    elif pct <= -35: rec, color = "SELL", "#FF1744"
    else:            rec, color = "HOLD", "#FFC107"

    confidence = min(abs(pct), 100)
    return {
        "recommendation": rec,
        "color":          color,
        "score":          score,
        "max_score":      max_score,
        "pct":            pct,
        "confidence":     confidence,
        "factors":        factors,
    }


# ── Risk Score ────────────────────────────────────────────────────────────────

def calculate_risk_score(df: pd.DataFrame, info: dict) -> dict:
    """Composite risk score: Low / Medium / High."""
    if df.empty:
        return {}

    risk  = 0
    total = 0
    facts = []

    def _risk(pts, label, detail):
        nonlocal risk, total
        total += 3
        risk  += pts
        level  = "🔴 High" if pts == 3 else ("🟡 Medium" if pts == 2 else "🟢 Low")
        facts.append({"Factor": label, "Detail": detail, "Risk": level})

    # Beta
    beta = info.get("beta")
    if beta is not None:
        beta = float(beta)
        if   beta > 1.5: _risk(3, "Market Beta", f"β = {beta:.2f} — high volatility vs index")
        elif beta > 1.0: _risk(2, "Market Beta", f"β = {beta:.2f} — above-market volatility")
        else:            _risk(1, "Market Beta", f"β = {beta:.2f} — low/defensive")

    # ATR-based daily volatility
    if "ATR" in df.columns:
        close   = float(df["Close"].iloc[-1])
        atr_val = df["ATR"].dropna()
        if not atr_val.empty:
            vol_pct = (float(atr_val.iloc[-1]) / close) * 100
            if   vol_pct > 3.0: _risk(3, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")
            elif vol_pct > 1.5: _risk(2, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")
            else:               _risk(1, "Daily Volatility (ATR)", f"{vol_pct:.2f}% avg daily range")

    # Debt load (Debt / Market Cap)
    debt   = info.get("totalDebt")
    mktcap = info.get("marketCap")
    if debt and mktcap and mktcap > 0:
        ratio = debt / mktcap
        if   ratio > 0.6: _risk(3, "Debt / Mkt Cap", f"{ratio:.2f} — high leverage")
        elif ratio > 0.3: _risk(2, "Debt / Mkt Cap", f"{ratio:.2f} — moderate leverage")
        else:             _risk(1, "Debt / Mkt Cap", f"{ratio:.2f} — low leverage")

    # 52-week range position
    h52 = info.get("fiftyTwoWeekHigh")
    l52 = info.get("fiftyTwoWeekLow")
    if h52 and l52 and h52 != l52 and not df.empty:
        pos = (float(df["Close"].iloc[-1]) - l52) / (h52 - l52)
        if   pos < 0.25: _risk(3, "52W Position", f"{pos*100:.0f}% of range — near lows")
        elif pos > 0.80: _risk(2, "52W Position", f"{pos*100:.0f}% of range — near highs")
        else:            _risk(1, "52W Position", f"{pos*100:.0f}% of range — mid range")

    # Profit margin
    margin = info.get("profitMargins")
    if margin is not None:
        if   margin < 0:    _risk(3, "Profitability", f"Negative margin ({margin*100:.1f}%)")
        elif margin < 0.05: _risk(2, "Profitability", f"Thin margin ({margin*100:.1f}%)")
        else:               _risk(1, "Profitability", f"Healthy margin ({margin*100:.1f}%)")

    if total == 0:
        return {}

    pct = (risk / total) * 100
    if   pct >= 60: level, color, emoji = "HIGH",   "#FF1744", "🔴"
    elif pct >= 35: level, color, emoji = "MEDIUM", "#FFC107", "🟡"
    else:           level, color, emoji = "LOW",    "#00C853", "🟢"

    return {"level": level, "color": color, "emoji": emoji, "pct": pct, "factors": facts}


# ── Trend Reversal Alerts ─────────────────────────────────────────────────────

def detect_alerts(df: pd.DataFrame) -> list:
    """Return list of (emoji, title, description) alert tuples."""
    alerts = []
    if df.empty or len(df) < 3:
        return alerts

    close  = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    def _crossed_up(s1, s2):
        return len(s1) >= 2 and len(s2) >= 2 and \
               float(s1.iloc[-2]) < float(s2.iloc[-2]) and \
               float(s1.iloc[-1]) > float(s2.iloc[-1])

    def _crossed_dn(s1, s2):
        return len(s1) >= 2 and len(s2) >= 2 and \
               float(s1.iloc[-2]) > float(s2.iloc[-2]) and \
               float(s1.iloc[-1]) < float(s2.iloc[-1])

    # RSI crosses
    if "RSI" in df.columns:
        rsi = df["RSI"].dropna()
        thirty  = pd.Series([30] * len(rsi), index=rsi.index)
        seventy = pd.Series([70] * len(rsi), index=rsi.index)
        if _crossed_up(rsi, thirty):
            alerts.append(("🟢", "RSI Oversold Reversal",  "RSI crossed above 30 — potential bullish reversal"))
        if _crossed_dn(rsi, seventy):
            alerts.append(("🔴", "RSI Overbought Reversal","RSI crossed below 70 — potential bearish reversal"))

    # MACD crossover
    if "MACD" in df.columns and "MACD_signal" in df.columns:
        macd = df["MACD"].dropna()
        sig  = df["MACD_signal"].dropna()
        if _crossed_up(macd, sig):
            alerts.append(("🟢", "MACD Bullish Crossover", "MACD crossed above signal line"))
        if _crossed_dn(macd, sig):
            alerts.append(("🔴", "MACD Bearish Crossover", "MACD crossed below signal line"))

    # Price vs SMA20
    if "SMA20" in df.columns:
        sma20 = df["SMA20"].dropna()
        if _crossed_up(close.reindex(sma20.index), sma20):
            alerts.append(("🟢", "Price crossed SMA20 ↑",  "Bullish: price moved above 20-day average"))
        if _crossed_dn(close.reindex(sma20.index), sma20):
            alerts.append(("🔴", "Price crossed SMA20 ↓",  "Bearish: price dropped below 20-day average"))

    # Golden / Death cross
    if "SMA50" in df.columns and "SMA200" in df.columns:
        sma50  = df["SMA50"].dropna()
        sma200 = df["SMA200"].dropna()
        idx    = sma50.index.intersection(sma200.index)
        if len(idx) >= 2:
            s50, s200 = sma50.reindex(idx), sma200.reindex(idx)
            if _crossed_up(s50, s200):
                alerts.append(("🟢", "Golden Cross! SMA50 > SMA200", "Strong long-term bullish signal"))
            if _crossed_dn(s50, s200):
                alerts.append(("🔴", "Death Cross! SMA50 < SMA200",  "Strong long-term bearish signal"))

    # Bollinger Band extremes
    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        last_close = float(close.iloc[-1])
        if last_close > float(df["BB_upper"].iloc[-1]):
            alerts.append(("🟡", "Bollinger Upper Breakout", "Price above upper band — overbought or momentum"))
        elif last_close < float(df["BB_lower"].iloc[-1]):
            alerts.append(("🟡", "Bollinger Lower Breakdown","Price below lower band — oversold or downtrend"))

    # Volume spike (≥ 2× 20-day average)
    if "Vol_SMA20" in df.columns:
        v_now = float(volume.iloc[-1])
        v_avg = float(df["Vol_SMA20"].iloc[-1])
        if v_avg > 0 and v_now >= 2 * v_avg:
            alerts.append(("🟡", "Volume Spike Detected", f"Volume is {v_now/v_avg:.1f}× the 20-day average"))

    if not alerts:
        alerts.append(("✅", "No Active Alerts", "No trend reversal signals detected currently"))

    return alerts


# ── Display: Recommendation + Risk ───────────────────────────────────────────

def show_recommendation_risk(rec: dict, risk: dict):
    col_rec, col_risk = st.columns(2)

    # Recommendation
    with col_rec:
        if rec:
            r     = rec["recommendation"]
            color = rec["color"]
            conf  = rec["confidence"]
            score = rec["score"]
            mx    = rec["max_score"]
            st.markdown(
                f"<div style='background:rgba(0,0,0,0.3);border:2px solid {color};"
                f"border-radius:12px;padding:1rem;text-align:center;'>"
                f"<div style='font-size:0.85rem;color:#aaa;'>Overall Recommendation</div>"
                f"<div style='font-size:2.4rem;font-weight:800;color:{color};letter-spacing:2px;'>{r}</div>"
                f"<div style='font-size:0.8rem;color:#aaa;'>Confidence: {conf:.0f}% &nbsp;|&nbsp; Score: {score}/{mx}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.expander("View scoring factors"):
                st.dataframe(pd.DataFrame(rec["factors"]), use_container_width=True, hide_index=True)
        else:
            st.info("Not enough data for recommendation.")

    # Risk
    with col_risk:
        if risk:
            lvl   = risk["level"]
            color = risk["color"]
            emoji = risk["emoji"]
            pct   = risk["pct"]
            st.markdown(
                f"<div style='background:rgba(0,0,0,0.3);border:2px solid {color};"
                f"border-radius:12px;padding:1rem;text-align:center;'>"
                f"<div style='font-size:0.85rem;color:#aaa;'>Risk Score</div>"
                f"<div style='font-size:2.4rem;font-weight:800;color:{color};'>{emoji} {lvl}</div>"
                f"<div style='font-size:0.8rem;color:#aaa;'>Risk Index: {pct:.0f} / 100</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.expander("View risk breakdown"):
                st.dataframe(pd.DataFrame(risk["factors"]), use_container_width=True, hide_index=True)
        else:
            st.info("Not enough data for risk score.")


# ── Display: Alerts ───────────────────────────────────────────────────────────

def show_alerts(alerts: list):
    st.subheader("🔔 Trend Reversal Alerts")
    if not alerts:
        st.info("No alerts.")
        return

    for emoji, title, desc in alerts:
        if emoji == "🟢":
            bg, border = "rgba(0,200,83,0.1)",  "#00C853"
        elif emoji == "🔴":
            bg, border = "rgba(255,23,68,0.1)",  "#FF1744"
        elif emoji == "🟡":
            bg, border = "rgba(255,193,7,0.1)",  "#FFC107"
        else:
            bg, border = "rgba(100,100,100,0.1)","#888"

        st.markdown(
            f"<div style='background:{bg};border-left:4px solid {border};"
            f"border-radius:6px;padding:0.6rem 1rem;margin-bottom:0.5rem;'>"
            f"<strong>{emoji} {title}</strong><br>"
            f"<span style='font-size:0.85rem;color:#ccc;'>{desc}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Market Overview ─────────────────────────────────────────────────────────────

def show_market_overview():
    st.subheader("Market Overview")
    cols = st.columns(len(INDICES))
    for col, (name, sym) in zip(cols, INDICES.items()):
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist["Close"].iloc[-2]
                curr_close = hist["Close"].iloc[-1]
                chg = curr_close - prev_close
                pct = (chg / prev_close) * 100
                arrow = "▲" if chg >= 0 else "▼"
                clr   = "#00C853" if chg >= 0 else "#FF1744"
                col.metric(
                    label=name,
                    value=f"{curr_close:,.2f}",
                    delta=f"{arrow} {abs(pct):.2f}%",
                )
            else:
                col.metric(label=name, value="N/A")
        except Exception:
            col.metric(label=name, value="N/A")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def sidebar_controls():
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Flag_of_India.svg/320px-Flag_of_India.svg.png",
                 width=60)
        st.markdown("## Indian Stock Analyzer")
        st.markdown("---")

        mode = st.radio("Stock Selection", ["Popular Stocks", "Custom Ticker"])

        if mode == "Popular Stocks":
            name = st.selectbox("Select Stock", list(POPULAR_STOCKS.keys()))
            ticker = POPULAR_STOCKS[name]
        else:
            ticker = st.text_input(
                "Enter NSE/BSE Ticker",
                value="RELIANCE.NS",
                help="Add .NS for NSE (e.g. RELIANCE.NS) or .BO for BSE (e.g. RELIANCE.BO)",
            ).upper()

        st.markdown("---")
        period_label = st.selectbox("Time Period", list(PERIODS.keys()), index=3)
        period, interval = PERIODS[period_label]

        st.markdown("---")
        chart_type = st.selectbox("Chart Type", ["Candlestick", "Line"])
        show_ma    = st.checkbox("Show Moving Averages", value=True)
        show_bb    = st.checkbox("Show Bollinger Bands", value=True)

        st.markdown("---")
        st.markdown("**Compare with Index**")
        compare_index = st.selectbox("Index", ["None"] + list(INDICES.keys()))

        st.markdown("---")
        st.markdown("**Target & Stop Loss**")
        sl_method   = st.selectbox("Method", ["ATR", "Swing High/Low", "Fibonacci"], key="sl_method")
        atr_mult_sl = st.slider("ATR Multiplier (SL)", 0.5, 3.0, 1.5, 0.25,
                                help="Stop Loss = Price − (multiplier × ATR)",
                                disabled=(sl_method != "ATR"))
        show_levels_on_chart = st.checkbox("Show levels on chart", value=True)

        st.markdown("---")
        st.caption("Data sourced from Yahoo Finance. Refresh every 5 min.")

    return ticker, period, interval, chart_type, show_ma, show_bb, compare_index, sl_method, atr_mult_sl, show_levels_on_chart


# ── Fundamental Analysis Panel ─────────────────────────────────────────────────

def show_fundamentals(info: dict):
    st.subheader("Fundamental Analysis")

    # Show notice if data is sparse (t.info likely failed; financial-statement fallbacks used)
    key_fields = ["marketCap", "trailingPE", "totalRevenue", "priceToBook",
                  "trailingEps", "profitMargins"]
    filled = sum(1 for k in key_fields if info.get(k) is not None)
    if filled == 0:
        st.warning(
            "⚠️ Fundamental data could not be loaded from Yahoo Finance for this ticker. "
            "This can happen due to rate-limiting or network restrictions on the server. "
            "Try refreshing the page or selecting a different time period to clear the cache."
        )
    elif filled < 3:
        st.info(
            "ℹ️ Some fundamental metrics are unavailable (retrieved from financial statements). "
            "P/E, margins and debt figures may differ slightly from Yahoo Finance's displayed values."
        )

    def g(key, default=None):
        return info.get(key, default)

    def fmt_div(val):
        """yfinance 1.x returns dividendYield already as a % value (e.g. 0.39 = 0.39%)."""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        # If < 1 it's in decimal fraction form (old yfinance); if ≥ 1 treat as % directly
        return f"{val:.2f}%" if val >= 1 else f"{val * 100:.2f}%"

    def safe_pct(key):
        v = g(key)
        if v is None:
            return "N/A"
        try:
            return fmt_pct(v)
        except Exception:
            return "N/A"

    # ── Key metrics grid ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Market Cap",    fmt_currency(g("marketCap")))
        st.metric("P/E Ratio",     fmt_num(g("trailingPE")))
        st.metric("Forward P/E",   fmt_num(g("forwardPE")))
    with col2:
        st.metric("P/B Ratio",     fmt_num(g("priceToBook")))
        st.metric("EPS (TTM)",     fmt_num(g("trailingEps")))
        st.metric("Revenue",       fmt_currency(g("totalRevenue")))
    with col3:
        st.metric("Div. Yield",    fmt_div(g("dividendYield")))
        st.metric("Beta",          fmt_num(g("beta")))
        st.metric("Profit Margin", safe_pct("profitMargins"))
    with col4:
        st.metric("52W High",      fmt_num(g("fiftyTwoWeekHigh")))
        st.metric("52W Low",       fmt_num(g("fiftyTwoWeekLow")))
        st.metric("Avg Volume",    f"{g('averageVolume'):,}" if g("averageVolume") else "N/A")

    st.markdown("---")

    # ── Valuation snapshot bar ────────────────────────────────────────────────
    pe  = g("trailingPE")
    pb  = g("priceToBook")
    eps = g("trailingEps")
    if any(v is not None for v in [pe, pb, eps]):
        vc1, vc2, vc3, vc4 = st.columns(4)
        vc1.metric("Trailing P/E",  fmt_num(pe),  help="Lower = cheaper vs earnings")
        vc2.metric("Price/Book",    fmt_num(pb),  help="< 1 = trading below book value")
        vc3.metric("EPS (TTM)",     fmt_num(eps), help="Earnings per share, trailing 12 months")
        vc4.metric("Total Debt",    fmt_currency(g("totalDebt")))

    # ── Company info expander ─────────────────────────────────────────────────
    with st.expander("Company Details", expanded=True):
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**Sector:** {g('sector', 'N/A')}")
            st.markdown(f"**Industry:** {g('industry', 'N/A')}")
            st.markdown(f"**Employees:** {g('fullTimeEmployees', 0):,}" if g("fullTimeEmployees") else "**Employees:** N/A")
            st.markdown(f"**Country:** {g('country', 'N/A')}")
            st.markdown(f"**Exchange:** {g('exchange', 'N/A')}")
            st.markdown(f"**Currency:** {g('currency', 'N/A')}")
        with cols[1]:
            st.markdown(f"**Gross Margin:** {safe_pct('grossMargins')}")
            st.markdown(f"**Operating Margin:** {safe_pct('operatingMargins')}")
            st.markdown(f"**Profit Margin:** {safe_pct('profitMargins')}")
            st.markdown(f"**ROE:** {safe_pct('returnOnEquity')}")
            st.markdown(f"**ROA:** {safe_pct('returnOnAssets')}")
            st.markdown(f"**Operating CF:** {fmt_currency(g('operatingCashflow'))}")

        summary = g("longBusinessSummary", "")
        if summary:
            st.markdown("**About:**")
            st.info(summary[:700] + ("…" if len(summary) > 700 else ""))


# ── Signals Panel ──────────────────────────────────────────────────────────────

def show_signals(signals: dict):
    st.subheader("Technical Signals")
    if not signals:
        st.info("Not enough data to generate signals.")
        return

    buy_count  = sum(1 for s, _ in signals.values() if s == "BUY")
    sell_count = sum(1 for s, _ in signals.values() if s == "SELL")
    hold_count = sum(1 for s, _ in signals.values() if s == "HOLD")
    total      = len(signals)

    # Overall sentiment
    if buy_count > sell_count and buy_count > hold_count:
        overall_color, overall_label = "#00C853", "BULLISH"
    elif sell_count > buy_count and sell_count > hold_count:
        overall_color, overall_label = "#FF1744", "BEARISH"
    else:
        overall_color, overall_label = "#FFC107", "NEUTRAL"

    st.markdown(
        f"<div style='text-align:center; font-size:1.5rem; font-weight:700; color:{overall_color};"
        f"border:2px solid {overall_color}; border-radius:8px; padding:0.5rem;'>"
        f"Overall: {overall_label}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='text-align:center;margin:0.5rem 0;'>"
                f"<span class='signal-buy'>BUY {buy_count}</span>&nbsp;"
                f"<span class='signal-hold'>HOLD {hold_count}</span>&nbsp;"
                f"<span class='signal-sell'>SELL {sell_count}</span></div>",
                unsafe_allow_html=True)

    # Signal table
    rows = []
    for indicator, (signal, reason) in signals.items():
        emoji = "🟢" if signal == "BUY" else ("🔴" if signal == "SELL" else "🟡")
        rows.append({"Indicator": indicator, "Signal": f"{emoji} {signal}", "Reason": reason})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Index Comparison Chart ─────────────────────────────────────────────────────

def show_comparison(stock_df: pd.DataFrame, stock_ticker: str, index_name: str, period: str, interval: str):
    if index_name == "None":
        return

    idx_sym = INDICES[index_name]
    idx_df  = fetch_stock_data(idx_sym, period, interval)
    if idx_df.empty or stock_df.empty:
        return

    st.subheader(f"Performance vs {index_name}")

    # Normalise to 100
    s_norm = (stock_df["Close"] / stock_df["Close"].iloc[0] * 100).squeeze()
    i_norm = (idx_df["Close"]   / idx_df["Close"].iloc[0]   * 100).squeeze()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=stock_df.index, y=s_norm,
                             mode="lines", name=stock_ticker,
                             line=dict(color="#FF6B35", width=2)))
    fig.add_trace(go.Scatter(x=idx_df.index, y=i_norm,
                             mode="lines", name=index_name,
                             line=dict(color="#00BCD4", width=2)))
    fig.update_layout(
        template="plotly_dark", height=350,
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        yaxis_title="Normalised Value (Base=100)",
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key="comparison_chart")


# ── Returns Analysis ───────────────────────────────────────────────────────────

def show_returns(df: pd.DataFrame):
    st.subheader("Returns Analysis")
    close = df["Close"].squeeze()

    periods = {
        "1W":  7,
        "1M":  21,
        "3M":  63,
        "6M":  126,
        "1Y":  252,
    }

    rows = []
    for label, days in periods.items():
        if len(close) > days:
            ret = (close.iloc[-1] / close.iloc[-days] - 1) * 100
            rows.append({"Period": label, "Return (%)": round(ret, 2)})

    if rows:
        ret_df = pd.DataFrame(rows)
        colors = ["#00C853" if r >= 0 else "#FF1744" for r in ret_df["Return (%)"]]
        fig = go.Figure(go.Bar(
            x=ret_df["Period"], y=ret_df["Return (%)"],
            marker_color=colors, text=ret_df["Return (%)"].map(lambda x: f"{x:+.2f}%"),
            textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark", height=300,
            paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
            yaxis_title="Return (%)",
            margin=dict(l=40, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, key="returns_chart")


# ── Volatility Section ─────────────────────────────────────────────────────────

def show_volatility(df: pd.DataFrame):
    close = df["Close"].squeeze()
    daily_ret = close.pct_change().dropna()
    ann_vol   = daily_ret.std() * np.sqrt(252) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Annualised Volatility", f"{ann_vol:.2f}%")
    col2.metric("Max Daily Gain",  f"{daily_ret.max()*100:+.2f}%")
    col3.metric("Max Daily Loss",  f"{daily_ret.min()*100:+.2f}%")

    fig = px.histogram(
        daily_ret * 100, nbins=50,
        labels={"value": "Daily Return (%)"},
        title="Daily Return Distribution",
        color_discrete_sequence=["#FF6B35"],
    )
    fig.update_layout(
        template="plotly_dark", height=300,
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        showlegend=False, margin=dict(l=40, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key="volatility_chart")


# ── Main App ───────────────────────────────────────────────────────────────────

def main():
    st.markdown('<div class="main-header">🇮🇳 Indian Stock Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">NSE & BSE  |  Technical & Fundamental Analysis  |  Live Data</div>',
                unsafe_allow_html=True)

    ticker, period, interval, chart_type, show_ma, show_bb, compare_index, sl_method, atr_mult_sl, show_levels_on_chart = sidebar_controls()

    # Market overview at top
    with st.expander("📊 Market Overview", expanded=True):
        show_market_overview()

    st.markdown("---")

    # Fetch data
    with st.spinner(f"Fetching data for {ticker}…"):
        df   = fetch_stock_data(ticker, period, interval)
        info = fetch_info(ticker)

    if df.empty:
        st.error("No data returned. Check the ticker symbol and try again.")
        return

    df     = add_indicators(df)
    levels = calculate_levels(df, method=sl_method, atr_mult_sl=atr_mult_sl)
    rec    = calculate_recommendation(df, info)
    risk   = calculate_risk_score(df, info)
    alerts = detect_alerts(df)

    # ── Stock header ──────────────────────────────────────────────────────────
    name  = info.get("longName", ticker)
    curr  = info.get("currency", "INR")
    sym   = "₹" if curr in ("INR", "INr") else curr + " "

    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_close
    day_chg    = last_close - prev_close
    day_pct    = (day_chg / prev_close) * 100

    col_a, col_b, col_c, col_d, col_e = st.columns([3, 1.5, 1.5, 1.5, 1.5])
    col_a.markdown(f"### {name}\n`{ticker}`")
    col_b.metric("Last Price",  f"{sym}{last_close:,.2f}")
    col_c.metric("Day Change",  f"{sym}{day_chg:+,.2f}", f"{day_pct:+.2f}%")
    col_d.metric("Open",        f"{sym}{float(df['Open'].iloc[-1]):,.2f}")
    col_e.metric("High / Low",  f"{sym}{float(df['High'].iloc[-1]):,.2f} / {sym}{float(df['Low'].iloc[-1]):,.2f}")

    st.markdown("---")
    show_recommendation_risk(rec, risk)
    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📈 Price Chart", "🎯 Target & Stop Loss", "📊 Technical Indicators", "🏢 Fundamentals", "📉 Analysis", "📋 Raw Data"]
    )

    with tab1:
        chart_levels = levels if show_levels_on_chart else None
        st.plotly_chart(
            build_price_chart(df, ticker, chart_type, show_bb, show_ma, levels=chart_levels),
            use_container_width=True,
            key="price_chart_tab1",
        )
        show_comparison(df, ticker, compare_index, period, interval)

    with tab2:
        show_target_stop_loss(levels, sym)
        st.markdown("---")
        st.plotly_chart(
            build_price_chart(df, ticker, chart_type, show_bb, show_ma, levels=levels),
            use_container_width=True,
            key="price_chart_tab2",
        )

    with tab3:
        show_alerts(alerts)
        st.markdown("---")
        signals = generate_signals(df)
        show_signals(signals)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(build_macd_chart(df), use_container_width=True, key="macd_chart")
        with col2:
            st.plotly_chart(build_stoch_chart(df), use_container_width=True, key="stoch_chart")

    with tab4:
        show_fundamentals(info)

    with tab5:
        st.subheader("Returns")
        show_returns(df)
        st.markdown("---")
        st.subheader("Volatility")
        show_volatility(df)

    with tab6:
        st.subheader("Historical Data")
        display_df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        display_df.index = display_df.index.date
        display_df = display_df.sort_index(ascending=False)
        display_df.columns = ["Open (₹)", "High (₹)", "Low (₹)", "Close (₹)", "Volume"]
        st.dataframe(display_df.style.format({
            "Open (₹)":  "₹{:.2f}",
            "High (₹)":  "₹{:.2f}",
            "Low (₹)":   "₹{:.2f}",
            "Close (₹)": "₹{:.2f}",
            "Volume":    "{:,.0f}",
        }), use_container_width=True)

        csv = display_df.to_csv().encode("utf-8")
        st.download_button("Download CSV", csv, f"{ticker}_data.csv", "text/csv")


if __name__ == "__main__":
    main()
