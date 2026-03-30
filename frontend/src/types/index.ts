export interface OHLCVRow {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  ema20: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_mid: number | null;
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  stoch_k: number | null;
  stoch_d: number | null;
  atr: number | null;
  vol_sma20: number | null;
}

export interface StockMeta {
  last_close: number;
  prev_close: number;
  day_change: number;
  day_change_pct: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  long_name: string;
}

export interface OHLCVResponse {
  ticker: string;
  period: string;
  interval: string;
  currency: string;
  rows: OHLCVRow[];
  meta: StockMeta;
}

export interface SignalItem {
  signal: "BUY" | "HOLD" | "SELL";
  reason: string;
}

export interface AlertItem {
  color: "green" | "red" | "yellow";
  title: string;
  description: string;
}

export interface Factor {
  Factor: string;
  Signal?: string;
  Points?: string;
  Detail?: string;
  Risk?: string;
}

export interface Recommendation {
  recommendation: "BUY" | "HOLD" | "SELL";
  color: string;
  score: number;
  max_score: number;
  pct: number;
  confidence: number;
  factors: Factor[];
}

export interface RiskScore {
  level: "LOW" | "MEDIUM" | "HIGH";
  color: string;
  pct: number;
  factors: Factor[];
}

export interface Levels {
  current: number;
  stop_loss: number;
  risk: number;
  risk_pct: number;
  atr: number;
  method: string;
  targets: Record<string, number>;
  fib_levels: Record<string, number>;
}

export interface AnalysisResponse {
  levels: Levels;
  signals: Record<string, SignalItem>;
  alerts: AlertItem[];
  recommendation: Recommendation;
  risk: RiskScore;
}

export interface Fundamentals {
  ticker: string;
  long_name: string | null;
  sector: string | null;
  industry: string | null;
  country: string | null;
  exchange: string | null;
  currency: string | null;
  employees: number | null;
  summary: string | null;
  market_cap: number | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  price_to_book: number | null;
  trailing_eps: number | null;
  dividend_yield: number | null;
  beta: number | null;
  total_revenue: number | null;
  gross_margins: number | null;
  operating_margins: number | null;
  profit_margins: number | null;
  roe: number | null;
  roa: number | null;
  total_debt: number | null;
  operating_cashflow: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  average_volume: number | null;
  data_quality: "full" | "partial" | "minimal";
}

export interface IndexQuote {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
}

export interface MarketOverview {
  indices: IndexQuote[];
}

export interface StockItem {
  name: string;
  ticker: string;
}

export interface PeriodItem {
  label: string;
  period: string;
  interval: string;
}
