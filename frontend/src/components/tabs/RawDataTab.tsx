"use client";

import type { OHLCVRow } from "@/types";

interface Props {
  rows: OHLCVRow[];
  ticker: string;
}

const COLS: [keyof OHLCVRow, string][] = [
  ["date", "Date"],
  ["open", "Open"],
  ["high", "High"],
  ["low", "Low"],
  ["close", "Close"],
  ["volume", "Volume"],
  ["sma20", "SMA20"],
  ["sma50", "SMA50"],
  ["ema20", "EMA20"],
  ["bb_upper", "BB Upper"],
  ["bb_lower", "BB Lower"],
  ["rsi", "RSI"],
  ["macd", "MACD"],
  ["atr", "ATR"],
];

function fmt(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  return String(v);
}

function downloadCSV(rows: OHLCVRow[], ticker: string) {
  const header = COLS.map(([, h]) => h).join(",");
  const lines  = rows.map(r => COLS.map(([k]) => fmt(r[k])).join(","));
  const blob   = new Blob([[header, ...lines].join("\n")], { type: "text/csv" });
  const url    = URL.createObjectURL(blob);
  const a      = document.createElement("a");
  a.href = url;
  a.download = `${ticker}_data.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function RawDataTab({ rows, ticker }: Props) {
  const reversed = [...rows].reverse();

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-400">{rows.length} rows</div>
        <button
          onClick={() => downloadCSV(rows, ticker)}
          className="text-sm px-4 py-1.5 rounded-lg font-medium transition-colors"
          style={{ background: "#FF6B35", color: "white" }}
        >
          ⬇ Download CSV
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg"
           style={{ border: "1px solid rgba(255,255,255,0.08)", maxHeight: 520 }}>
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10"
                 style={{ background: "#1E1E2E", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
            <tr>
              {COLS.map(([, h]) => (
                <th key={h} className="text-left px-3 py-2 text-gray-400 font-medium whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {reversed.map((r, i) => (
              <tr key={i} style={{
                borderTop: "1px solid rgba(255,255,255,0.04)",
                background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
              }}>
                {COLS.map(([k]) => (
                  <td key={k} className="px-3 py-1.5 text-gray-300 whitespace-nowrap">
                    {fmt(r[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
