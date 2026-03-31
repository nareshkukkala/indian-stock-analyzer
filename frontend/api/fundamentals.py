import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from _shared import fetch_info, json_safe  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        ticker = (qs.get("ticker", ["RELIANCE.NS"])[0]).upper()

        try:
            info = fetch_info(ticker)

            def _g(k):
                v = info.get(k)
                return json_safe(v)

            body = json_safe({
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
                "fifty_two_week_high": _g("fiftyTwoWeekHigh"),
                "fifty_two_week_low":  _g("fiftyTwoWeekLow"),
                "average_volume":     _g("averageVolume"),
                "data_quality":       info.get("_dataQuality", "minimal"),
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
