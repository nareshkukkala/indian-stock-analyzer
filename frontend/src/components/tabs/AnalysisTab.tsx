"use client";

import dynamic from "next/dynamic";
import type { OHLCVRow } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  rows: OHLCVRow[];
  ticker: string;
  sym: string;
}

const DARK = "#0E1117";

export default function AnalysisTab({ rows, ticker, sym }: Props) {
  const closes = rows.map(r => r.close ?? 0).filter(Boolean);
  if (closes.length < 2) return <div className="text-gray-400">Not enough data.</div>;

  // Daily returns
  const dailyReturns = closes.slice(1).map((c, i) => (c - closes[i]) / closes[i]);
  const annVol = (Math.sqrt(dailyReturns.reduce((s, r) => s + r * r, 0) / dailyReturns.length) * Math.sqrt(252) * 100);
  const mean   = dailyReturns.reduce((s, r) => s + r, 0) / dailyReturns.length;
  const maxDD  = (() => {
    let peak = closes[0], maxDd = 0;
    for (const c of closes) {
      if (c > peak) peak = c;
      const dd = (peak - c) / peak;
      if (dd > maxDd) maxDd = dd;
    }
    return maxDd * 100;
  })();

  // Period returns bar chart
  const periods: [string, number][] = [];
  const addPeriod = (label: string, nDays: number) => {
    if (closes.length > nDays) {
      const ret = ((closes[closes.length - 1] - closes[closes.length - 1 - nDays]) /
                    closes[closes.length - 1 - nDays]) * 100;
      periods.push([label, ret]);
    }
  };
  addPeriod("1W", 5);
  addPeriod("1M", 21);
  addPeriod("3M", 63);
  addPeriod("6M", 126);
  addPeriod("1Y", 252);

  const retColors = periods.map(([, r]) => r >= 0 ? "#00C853" : "#FF1744");

  const layoutBase = {
    template: "plotly_dark" as const,
    paper_bgcolor: DARK,
    plot_bgcolor: DARK,
    font: { color: "#e0e0e0" },
    margin: { l: 50, r: 20, t: 45, b: 40 },
    xaxis: { gridcolor: "rgba(255,255,255,0.05)" },
    yaxis: { gridcolor: "rgba(255,255,255,0.05)" },
  };

  return (
    <div className="space-y-5">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          ["Annualised Volatility", `${annVol.toFixed(2)}%`],
          ["Max Drawdown",          `−${maxDD.toFixed(2)}%`],
          ["Avg Daily Return",      `${(mean * 100).toFixed(3)}%`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg p-3 text-center"
               style={{ background: "#1E1E2E", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="text-xs text-gray-400">{label}</div>
            <div className="text-lg font-bold text-white mt-0.5">{value}</div>
          </div>
        ))}
      </div>

      {/* Period returns */}
      {periods.length > 0 && (
        <Plot
          data={[{
            type: "bar",
            x: periods.map(([l]) => l),
            y: periods.map(([, r]) => r),
            marker: { color: retColors },
            text: periods.map(([, r]) => `${r >= 0 ? "+" : ""}${r.toFixed(2)}%`),
            textposition: "outside",
            name: "Returns",
          } as Plotly.Data]}
          layout={{
            ...layoutBase,
            height: 280,
            title: { text: `${ticker} — Period Returns`, font: { size: 13 } },
            yaxis: { ...layoutBase.yaxis, title: "%" },
          } as unknown as Partial<Plotly.Layout>}
          config={{ responsive: true }}
          style={{ width: "100%" }}
          useResizeHandler
        />
      )}

      {/* Return distribution histogram */}
      <Plot
        data={[{
          type: "histogram",
          x: dailyReturns.map(r => r * 100),
          nbinsx: 40,
          marker: { color: "#FF6B35", opacity: 0.7 },
          name: "Daily Returns",
        } as Plotly.Data]}
        layout={{
          ...layoutBase,
          height: 280,
          title: { text: "Daily Return Distribution", font: { size: 13 } },
          xaxis: { ...layoutBase.xaxis, title: "Daily Return (%)" },
          yaxis: { ...layoutBase.yaxis, title: "Frequency" },
        } as unknown as Partial<Plotly.Layout>}
        config={{ responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  );
}
