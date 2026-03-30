"use client";

import { useState } from "react";
import type { Levels } from "@/types";
import { fmtCurrency } from "@/lib/formatters";

interface Props {
  levels?: Levels;
  sym: string;
}

export default function TargetStopLossTab({ levels, sym }: Props) {
  const [capital, setCapital]   = useState(100000);
  const [riskPct, setRiskPct]   = useState(1.0);
  const [entry, setEntry]       = useState<number | "">("");
  const [showFib, setShowFib]   = useState(false);
  const [showPos, setShowPos]   = useState(false);

  if (!levels) {
    return <div className="text-gray-400 mt-4">Not enough data to calculate levels.</div>;
  }

  const { current, stop_loss, risk, risk_pct, targets, fib_levels, atr, method } = levels;
  const entryPrice = entry === "" ? current : entry;

  const riskAmount   = capital * (riskPct / 100);
  const slDist       = entryPrice - stop_loss;
  const qty          = slDist > 0 ? Math.floor(riskAmount / slDist) : 0;
  const investAmount = qty * entryPrice;
  const maxLoss      = qty * slDist;

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-400">
        <span className="font-medium text-gray-300">Method: {method}</span>
        &nbsp;|&nbsp; ATR(14): {sym}{atr.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
      </div>

      {/* Level cards */}
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${2 + Object.keys(targets).length}, 1fr)` }}>
        <div className="level-card level-curr">
          <div className="text-xs text-gray-400">Current Price</div>
          <div className="text-xl font-bold" style={{ color: "#FF6B35" }}>
            {sym}{current.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="level-card level-sl">
          <div className="text-xs text-gray-400">Stop Loss</div>
          <div className="text-xl font-bold" style={{ color: "#FF1744" }}>
            {sym}{stop_loss.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </div>
          <div className="text-xs" style={{ color: "#FF1744" }}>
            −{sym}{risk.toFixed(2)} &nbsp; −{risk_pct.toFixed(2)}%
          </div>
        </div>
        {Object.entries(targets).map(([label, price], i) => {
          const upside    = price - current;
          const upsidePct = (upside / current) * 100;
          const rr        = risk > 0 ? upside / risk : 0;
          const cls       = ["level-t1","level-t2","level-t3"][i] ?? "level-t3";
          return (
            <div key={label} className={`level-card ${cls}`}>
              <div className="text-xs text-gray-400 truncate" title={label}>{label}</div>
              <div className="text-xl font-bold" style={{ color: "#00C853" }}>
                {sym}{price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs" style={{ color: "#00C853" }}>
                +{sym}{upside.toFixed(2)} &nbsp; +{upsidePct.toFixed(2)}%
              </div>
              <div className="text-xs text-gray-400">R:R = 1:{rr.toFixed(1)}</div>
            </div>
          );
        })}
      </div>

      {/* Fibonacci */}
      <div>
        <button onClick={() => setShowFib(!showFib)}
                className="text-sm text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1">
          {showFib ? "▲" : "▶"} Fibonacci Retracement Levels
        </button>
        {showFib && (
          <div className="mt-2 overflow-x-auto rounded-lg"
               style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
            <table className="w-full text-sm">
              <thead style={{ background: "rgba(255,255,255,0.04)" }}>
                <tr>
                  {["Fib Level", "Price", "Distance", "Distance %", "Zone"].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-gray-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(fib_levels).map(([label, price]) => {
                  const dist = price - current;
                  const distPct = (dist / current) * 100;
                  const zone = price < current ? "Support" : price > current ? "Resistance" : "Current";
                  return (
                    <tr key={label} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                      <td className="px-3 py-1.5 text-gray-300">{label}</td>
                      <td className="px-3 py-1.5">{sym}{price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td className="px-3 py-1.5" style={{ color: dist >= 0 ? "#00C853" : "#FF1744" }}>
                        {dist >= 0 ? "+" : ""}{dist.toFixed(2)}
                      </td>
                      <td className="px-3 py-1.5" style={{ color: dist >= 0 ? "#00C853" : "#FF1744" }}>
                        {dist >= 0 ? "+" : ""}{distPct.toFixed(2)}%
                      </td>
                      <td className="px-3 py-1.5">
                        <span className="text-xs px-2 py-0.5 rounded-full"
                              style={{ background: zone === "Support" ? "rgba(0,200,83,0.15)" : zone === "Resistance" ? "rgba(255,23,68,0.15)" : "rgba(255,107,53,0.15)",
                                       color: zone === "Support" ? "#00C853" : zone === "Resistance" ? "#FF1744" : "#FF6B35" }}>
                          {zone}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Position calculator */}
      <div>
        <button onClick={() => setShowPos(!showPos)}
                className="text-sm text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1">
          {showPos ? "▲" : "▶"} Position Size Calculator
        </button>
        {showPos && (
          <div className="mt-3 p-4 rounded-xl space-y-3"
               style={{ background: "#1E1E2E", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="text-xs text-gray-400">How many shares to buy based on your risk tolerance</div>
            <div className="grid grid-cols-3 gap-3">
              <label className="flex flex-col gap-1 text-xs text-gray-400">
                Total Capital (₹)
                <input type="number" value={capital} min={1000} step={10000}
                       onChange={e => setCapital(+e.target.value)}
                       className="rounded px-2 py-1.5 text-sm text-white"
                       style={{ background: "#13151F", border: "1px solid rgba(255,255,255,0.1)" }} />
              </label>
              <label className="flex flex-col gap-1 text-xs text-gray-400">
                Risk per trade (%)
                <input type="number" value={riskPct} min={0.1} max={10} step={0.5}
                       onChange={e => setRiskPct(+e.target.value)}
                       className="rounded px-2 py-1.5 text-sm text-white"
                       style={{ background: "#13151F", border: "1px solid rgba(255,255,255,0.1)" }} />
              </label>
              <label className="flex flex-col gap-1 text-xs text-gray-400">
                Entry Price (₹)
                <input type="number" value={entry} step={0.5}
                       placeholder={current.toFixed(2)}
                       onChange={e => setEntry(e.target.value === "" ? "" : +e.target.value)}
                       className="rounded px-2 py-1.5 text-sm text-white"
                       style={{ background: "#13151F", border: "1px solid rgba(255,255,255,0.1)" }} />
              </label>
            </div>
            {slDist > 0 ? (
              <div className="grid grid-cols-4 gap-3 mt-2">
                {[
                  ["Quantity", `${qty.toLocaleString()} shares`, undefined],
                  ["Investment", fmtCurrency(investAmount, sym), undefined],
                  ["Max Loss", fmtCurrency(maxLoss, sym), `−${riskPct.toFixed(1)}% of capital`],
                  ...Object.entries(targets).slice(0, 1).map(([l, p]) => [
                    `Profit at T1`, fmtCurrency(qty * (p - entryPrice), sym), l
                  ]),
                ].map(([label, value, sub], i) => (
                  <div key={i} className="rounded-lg p-3 text-center"
                       style={{ background: "#13151F", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div className="text-xs text-gray-400">{label}</div>
                    <div className="text-lg font-bold text-white mt-0.5">{value}</div>
                    {sub && <div className="text-xs text-red-400">{sub}</div>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-yellow-400 text-sm">
                ⚠️ Stop loss is above entry price — check your inputs.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
