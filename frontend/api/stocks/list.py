import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _shared import POPULAR_STOCKS, INDICES, PERIODS  # noqa: E402

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({
            "stocks":  [{"name": k, "ticker": v} for k, v in POPULAR_STOCKS.items()],
            "indices": [{"name": k, "symbol": v} for k, v in INDICES.items()],
            "periods": PERIODS,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
