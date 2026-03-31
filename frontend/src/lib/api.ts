import type {
  OHLCVResponse,
  AnalysisResponse,
  Fundamentals,
  MarketOverview,
} from "@/types";

// Empty string = same-origin (Vercel Python functions at /api/*).
// Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local for local dev.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function get<T>(path: string, params: Record<string, string | number> = {}): Promise<T> {
  const qs = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)])
  ).toString();
  const finalUrl = `${BASE}${path}${qs ? "?" + qs : ""}`;
  const res = await fetch(finalUrl, { cache: "no-store" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "API error");
  }
  return res.json();
}

export const api = {
  ohlcv: (ticker: string, period: string, interval: string) =>
    get<OHLCVResponse>("/api/stocks/ohlcv", { ticker, period, interval }),

  analysis: (ticker: string, period: string, interval: string, sl_method: string, atr_mult: number) =>
    get<AnalysisResponse>("/api/stocks/analysis", { ticker, period, interval, sl_method, atr_mult }),

  fundamentals: (ticker: string) =>
    get<Fundamentals>("/api/fundamentals", { ticker }),

  market: () =>
    get<MarketOverview>("/api/market/overview"),
};

// SWR key generators (keep keys consistent for cache)
export const keys = {
  ohlcv:   (t: string, p: string, i: string) => `/ohlcv/${t}/${p}/${i}`,
  analysis:(t: string, p: string, i: string, m: string, a: number) => `/analysis/${t}/${p}/${i}/${m}/${a}`,
  fundamentals: (t: string) => `/fundamentals/${t}`,
  market:  () => "/market",
};
