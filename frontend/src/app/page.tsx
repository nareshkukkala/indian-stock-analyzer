"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, keys } from "@/lib/api";
import { POPULAR_STOCKS, PERIODS, SL_METHODS } from "@/lib/constants";
import { currencySymbol } from "@/lib/formatters";
import MarketOverview from "@/components/MarketOverview";
import StockHeader from "@/components/StockHeader";
import RecRiskCards from "@/components/RecRiskCards";
import PriceTab from "@/components/tabs/PriceTab";
import TargetStopLossTab from "@/components/tabs/TargetStopLossTab";
import TechnicalTab from "@/components/tabs/TechnicalTab";
import FundamentalsTab from "@/components/tabs/FundamentalsTab";
import AnalysisTab from "@/components/tabs/AnalysisTab";
import RawDataTab from "@/components/tabs/RawDataTab";

const TABS = [
  "📈 Price Chart",
  "🎯 Target & Stop Loss",
  "📊 Technical Indicators",
  "🏢 Fundamentals",
  "📉 Analysis",
  "📋 Raw Data",
];

export default function Home() {
  const [mode, setMode] = useState<"popular" | "custom">("popular");
  const [stockName, setStockName] = useState(POPULAR_STOCKS[0].name);
  const [customTicker, setCustomTicker] = useState("RELIANCE.NS");
  const [periodIdx, setPeriodIdx] = useState(3);
  const [chartType, setChartType] = useState<"Candlestick" | "Line">("Candlestick");
  const [showMA, setShowMA] = useState(true);
  const [showBB, setShowBB] = useState(true);
  const [showLevels, setShowLevels] = useState(true);
  const [slMethod, setSlMethod] = useState("ATR");
  const [atrMult, setAtrMult] = useState(1.5);
  const [tab, setTab] = useState(0);

  const ticker =
    mode === "popular"
      ? (POPULAR_STOCKS.find((s) => s.name === stockName)?.ticker ?? "RELIANCE.NS")
      : customTicker.toUpperCase();
  const { period, interval } = PERIODS[periodIdx];

  const { data: ohlcv, isLoading, error } = useSWR(
    keys.ohlcv(ticker, period, interval),
    () => api.ohlcv(ticker, period, interval),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );
  const { data: analysis, isLoading: loadingAnalysis } = useSWR(
    keys.analysis(ticker, period, interval, slMethod, atrMult),
    () => api.analysis(ticker, period, interval, slMethod, atrMult),
    { revalidateOnFocus: false, dedupingInterval: 300_000 }
  );
  const { data: fundamentals, isLoading: loadingFund } = useSWR(
    keys.fundamentals(ticker),
    () => api.fundamentals(ticker),
    { revalidateOnFocus: false, dedupingInterval: 600_000 }
  );

  const sym = currencySymbol(ohlcv?.currency);

  return (
    <div className="flex flex-col min-h-screen" style={{ background: "#0E1117" }}>
      {/* Top bar */}
      <div
        style={{ background: "#0A0D14", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        className="px-4 py-2"
      >
        <div className="max-w-screen-2xl mx-auto flex items-center gap-3 flex-wrap">
          <span className="text-lg font-bold" style={{ color: "#FF6B35" }}>
            📈 Indian Stock Analyzer
          </span>
          <MarketOverview />
        </div>
      </div>

      <div className="flex flex-1 max-w-screen-2xl mx-auto w-full">
        {/* Sidebar */}
        <aside
          style={{
            background: "#13151F",
            borderRight: "1px solid rgba(255,255,255,0.06)",
            minWidth: 230,
            maxWidth: 250,
          }}
          className="p-4 flex flex-col gap-4 overflow-y-auto"
        >
          {/* Mode */}
          <div>
            <div className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">
              Stock Selection
            </div>
            <div className="flex gap-2">
              {(["popular", "custom"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className="flex-1 py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: mode === m ? "#FF6B35" : "rgba(255,255,255,0.06)",
                    color: mode === m ? "white" : "#999",
                  }}
                >
                  {m === "popular" ? "Popular" : "Custom"}
                </button>
              ))}
            </div>
          </div>

          {mode === "popular" ? (
            <div>
              <div className="text-xs text-gray-400 mb-1 font-semibold">Select Stock</div>
              <select
                value={stockName}
                onChange={(e) => setStockName(e.target.value)}
                className="w-full rounded px-2 py-1.5 text-sm"
                style={{
                  background: "#1E1E2E",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#e0e0e0",
                }}
              >
                {POPULAR_STOCKS.map((s) => (
                  <option key={s.ticker} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <div className="text-xs text-gray-400 mb-1 font-semibold">Enter Ticker</div>
              <input
                value={customTicker}
                onChange={(e) => setCustomTicker(e.target.value.toUpperCase())}
                placeholder="e.g. RELIANCE.NS"
                className="w-full rounded px-2 py-1.5 text-sm"
                style={{
                  background: "#1E1E2E",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "#e0e0e0",
                }}
              />
              <div className="text-xs text-gray-500 mt-1">Add .NS (NSE) or .BO (BSE)</div>
            </div>
          )}

          {/* Period */}
          <div>
            <div className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">
              Time Period
            </div>
            <div className="grid grid-cols-4 gap-1">
              {PERIODS.map((p, i) => (
                <button
                  key={p.label}
                  onClick={() => setPeriodIdx(i)}
                  className="py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: periodIdx === i ? "#FF6B35" : "rgba(255,255,255,0.06)",
                    color: periodIdx === i ? "white" : "#999",
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Chart options */}
          <div>
            <div className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">
              Chart Type
            </div>
            <div className="flex gap-2">
              {(["Candlestick", "Line"] as const).map((ct) => (
                <button
                  key={ct}
                  onClick={() => setChartType(ct)}
                  className="flex-1 py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: chartType === ct ? "#FF6B35" : "rgba(255,255,255,0.06)",
                    color: chartType === ct ? "white" : "#999",
                  }}
                >
                  {ct}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-1.5 mt-2">
              {(
                [
                  [showMA, setShowMA, "Show Moving Averages"],
                  [showBB, setShowBB, "Show Bollinger Bands"],
                  [showLevels, setShowLevels, "Show SL/Target Lines"],
                ] as [boolean, (v: boolean) => void, string][]
              ).map(([val, setter, label]) => (
                <label key={label} className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
                  <input
                    type="checkbox"
                    checked={val}
                    onChange={(e) => setter(e.target.checked)}
                    className="rounded accent-orange-500"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          {/* SL Method */}
          <div>
            <div className="text-xs text-gray-400 mb-1 font-semibold uppercase tracking-wider">
              SL Method
            </div>
            <select
              value={slMethod}
              onChange={(e) => setSlMethod(e.target.value)}
              className="w-full rounded px-2 py-1.5 text-sm"
              style={{
                background: "#1E1E2E",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#e0e0e0",
              }}
            >
              {SL_METHODS.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
            {slMethod === "ATR" && (
              <div className="mt-2">
                <div className="text-xs text-gray-400 mb-1">
                  ATR Multiplier: {atrMult.toFixed(1)}
                </div>
                <input
                  type="range"
                  min={0.5}
                  max={4}
                  step={0.5}
                  value={atrMult}
                  onChange={(e) => setAtrMult(Number(e.target.value))}
                  className="w-full accent-orange-500"
                />
              </div>
            )}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-4 min-w-0 overflow-hidden">
          {isLoading && (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <div className="text-3xl mb-3 animate-spin">⏳</div>
                <div>Loading data for {ticker}…</div>
                <div className="text-xs mt-1 text-gray-500">
                  Backend may need a moment to warm up on first request
                </div>
              </div>
            </div>
          )}

          {error && !isLoading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center text-red-400">
                <div className="text-2xl mb-2">⚠️</div>
                <div>Failed to load: {error.message}</div>
              </div>
            </div>
          )}

          {ohlcv && !isLoading && (
            <>
              <StockHeader meta={ohlcv.meta} ticker={ticker} sym={sym} />

              {analysis && (
                <div className="mt-3">
                  <RecRiskCards rec={analysis.recommendation} risk={analysis.risk} />
                </div>
              )}

              {/* Tab bar */}
              <div
                className="flex gap-1 mt-4 overflow-x-auto pb-1"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
              >
                {TABS.map((t, i) => (
                  <button
                    key={t}
                    onClick={() => setTab(i)}
                    className={`tab-btn ${tab === i ? "active" : ""}`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="mt-4">
                {tab === 0 && (
                  <PriceTab
                    rows={ohlcv.rows}
                    ticker={ticker}
                    chartType={chartType}
                    showMA={showMA}
                    showBB={showBB}
                    levels={showLevels ? analysis?.levels : undefined}
                  />
                )}
                {tab === 1 && <TargetStopLossTab levels={analysis?.levels} sym={sym} />}
                {tab === 2 && (
                  <TechnicalTab
                    rows={ohlcv.rows}
                    signals={analysis?.signals}
                    alerts={analysis?.alerts}
                  />
                )}
                {tab === 3 && (
                  <FundamentalsTab fundamentals={fundamentals ?? null} loading={loadingFund} />
                )}
                {tab === 4 && <AnalysisTab rows={ohlcv.rows} ticker={ticker} sym={sym} />}
                {tab === 5 && <RawDataTab rows={ohlcv.rows} ticker={ticker} />}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
