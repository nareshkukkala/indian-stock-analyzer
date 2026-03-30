"use client";

import dynamic from "next/dynamic";
import type { OHLCVRow, SignalItem, AlertItem } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  rows: OHLCVRow[];
  signals?: Record<string, SignalItem>;
  alerts?: AlertItem[];
}

const DARK = "#0E1117";

export default function TechnicalTab({ rows, signals, alerts }: Props) {
  const dates = rows.map(r => r.date);

  // MACD chart
  const macdTraces: object[] = [];
  if (rows.some(r => r.macd != null)) {
    const histColors = rows.map(r => (r.macd_hist ?? 0) >= 0 ? "#00C853" : "#FF1744");
    macdTraces.push(
      { type: "scatter", x: dates, y: rows.map(r => r.macd), mode: "lines", name: "MACD", line: { color: "#00BCD4", width: 2 } },
      { type: "scatter", x: dates, y: rows.map(r => r.macd_signal), mode: "lines", name: "Signal", line: { color: "#FF6B35", width: 1.5 } },
      { type: "bar", x: dates, y: rows.map(r => r.macd_hist), name: "Histogram", marker: { color: histColors } },
    );
  }

  // Stochastic chart
  const stochTraces: object[] = [];
  if (rows.some(r => r.stoch_k != null)) {
    stochTraces.push(
      { type: "scatter", x: dates, y: rows.map(r => r.stoch_k), mode: "lines", name: "%K", line: { color: "#00BCD4", width: 2 } },
      { type: "scatter", x: dates, y: rows.map(r => r.stoch_d), mode: "lines", name: "%D", line: { color: "#FF6B35", width: 1.5, dash: "dot" } },
    );
  }

  const chartLayout = (title: string, yRange?: [number, number]) => ({
    template: "plotly_dark" as const,
    paper_bgcolor: DARK, plot_bgcolor: DARK,
    height: 280,
    title: { text: title, font: { size: 13 } },
    margin: { l: 45, r: 20, t: 45, b: 35 },
    legend: { orientation: "h" as const },
    xaxis: { gridcolor: "rgba(255,255,255,0.05)" },
    yaxis: { gridcolor: "rgba(255,255,255,0.05)", ...(yRange ? { range: yRange } : {}) },
    shapes: title === "Stochastic" ? [
      { type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: 80, y1: 80, line: { color: "red",   width: 1, dash: "dash" } },
      { type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: 20, y1: 20, line: { color: "green", width: 1, dash: "dash" } },
    ] : title === "MACD" ? [
      { type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: 0, y1: 0, line: { color: "white", width: 1, opacity: 0.3 } },
    ] : [],
  });

  const signalCount = signals
    ? { BUY: 0, HOLD: 0, SELL: 0, ...Object.fromEntries(
        ["BUY","HOLD","SELL"].map(s => [s, Object.values(signals).filter(v => v.signal === s).length])
      )}
    : null;

  const alertColor = (c: AlertItem["color"]) =>
    c === "green" ? "#00C853" : c === "red" ? "#FF1744" : "#FFC107";

  return (
    <div className="space-y-5">
      {/* Alerts */}
      {alerts && alerts.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-gray-300 mb-2">🔔 Trend Reversal Alerts</div>
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg px-3 py-2"
                   style={{ background: "#1E1E2E", borderLeft: `3px solid ${alertColor(a.color)}` }}>
                <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                     style={{ background: alertColor(a.color) }} />
                <div>
                  <div className="text-sm font-medium text-white">{a.title}</div>
                  <div className="text-xs text-gray-400">{a.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Signals */}
      {signals && signalCount && (
        <div>
          <div className="text-sm font-semibold text-gray-300 mb-2">Technical Signals</div>
          <div className="flex gap-2 mb-3">
            {(["BUY","HOLD","SELL"] as const).map(s => (
              <span key={s} className="px-3 py-1 rounded-full text-xs font-medium"
                    style={{
                      background: s === "BUY" ? "#00C853" : s === "SELL" ? "#FF1744" : "#FFC107",
                      color: s === "HOLD" ? "black" : "white",
                    }}>
                {s} {signalCount[s]}
              </span>
            ))}
          </div>
          <div className="overflow-x-auto rounded-lg"
               style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
            <table className="w-full text-sm">
              <thead style={{ background: "rgba(255,255,255,0.04)" }}>
                <tr>
                  {["Indicator", "Signal", "Reason"].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-gray-400 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(signals).map(([name, item]) => (
                  <tr key={name} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                    <td className="px-3 py-2 text-gray-300">{name}</td>
                    <td className="px-3 py-2">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{
                              background: item.signal === "BUY" ? "#00C853" : item.signal === "SELL" ? "#FF1744" : "#FFC107",
                              color: item.signal === "HOLD" ? "black" : "white",
                            }}>
                        {item.signal === "BUY" ? "🟢" : item.signal === "SELL" ? "🔴" : "🟡"} {item.signal}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-400">{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-4">
        {macdTraces.length > 0 && (
          <Plot data={macdTraces as Plotly.Data[]}
                layout={chartLayout("MACD") as unknown as Partial<Plotly.Layout>}
                config={{ responsive: true }}
                style={{ width: "100%" }}
                useResizeHandler />
        )}
        {stochTraces.length > 0 && (
          <Plot data={stochTraces as Plotly.Data[]}
                layout={chartLayout("Stochastic", [0, 100]) as unknown as Partial<Plotly.Layout>}
                config={{ responsive: true }}
                style={{ width: "100%" }}
                useResizeHandler />
        )}
      </div>
    </div>
  );
}
