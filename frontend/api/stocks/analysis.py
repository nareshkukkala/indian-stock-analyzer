import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _shared import (  # noqa: E402
    fetch_ohlcv, fetch_info, add_indicators,
    generate_signals, calculate_levels, calculate_recommendation,
    calculate_risk_score, detect_alerts, json_safe,
)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        ticker    = (qs.get("ticker",    ["RELIANCE.NS"])[0]).upper()
        period    =  qs.get("period",    ["6mo"])[0]
        interval  =  qs.get("interval",  ["1d"])[0]
        sl_method =  qs.get("sl_method", ["ATR"])[0]
        atr_mult  =  float(qs.get("atr_mult", ["1.5"])[0])

        try:
            df   = fetch_ohlcv(ticker, period, interval)
            if df.empty:
                self._err(404, "No data."); return
            df   = add_indicators(df)
            info = fetch_info(ticker)

            body = json_safe({
                "levels":         calculate_levels(df, method=sl_method, atr_mult=atr_mult),
                "signals":        generate_signals(df),
                "alerts":         detect_alerts(df),
                "recommendation": calculate_recommendation(df, info),
                "risk":           calculate_risk_score(df, info),
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
