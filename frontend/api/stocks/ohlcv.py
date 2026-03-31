import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _shared import fetch_ohlcv, fetch_info, add_indicators, df_to_rows, json_safe  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        ticker   = (qs.get("ticker",   ["RELIANCE.NS"])[0]).upper()
        period   =  qs.get("period",   ["6mo"])[0]
        interval =  qs.get("interval", ["1d"])[0]

        try:
            df = fetch_ohlcv(ticker, period, interval)
            if df.empty:
                self._err(404, "No data returned for this ticker/period.")
                return

            df   = add_indicators(df)
            info = fetch_info(ticker)

            last_close  = float(df["Close"].iloc[-1])
            prev_close  = float(df["Close"].iloc[-2]) if len(df) >= 2 else last_close
            day_chg     = last_close - prev_close
            day_chg_pct = (day_chg / prev_close) * 100 if prev_close else 0

            body = json_safe({
                "ticker":   ticker,
                "period":   period,
                "interval": interval,
                "currency": info.get("currency", "INR"),
                "rows":     df_to_rows(df),
                "meta": {
                    "last_close":     last_close,
                    "prev_close":     prev_close,
                    "day_change":     round(day_chg, 2),
                    "day_change_pct": round(day_chg_pct, 2),
                    "open":           float(df["Open"].iloc[-1]),
                    "high":           float(df["High"].iloc[-1]),
                    "low":            float(df["Low"].iloc[-1]),
                    "volume":         int(df["Volume"].iloc[-1]),
                    "long_name":      info.get("longName", ticker),
                },
            })
            self._ok(body)
        except Exception as e:
            self._err(502, str(e))

    def _ok(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code, msg):
        body = json.dumps({"detail": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
