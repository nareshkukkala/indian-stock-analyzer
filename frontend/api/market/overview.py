import json
import os
import sys
import math
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _shared import INDICES  # noqa: E402

import yfinance as yf
import pandas as pd


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
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

            body = json.dumps({"indices": result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"detail": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        pass
