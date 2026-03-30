"use client";

import dynamic from "next/dynamic";
import type { OHLCVRow, Levels } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  rows: OHLCVRow[];
  ticker: string;
  chartType: "Candlestick" | "Line";
  showMA: boolean;
  showBB: boolean;
  levels?: Levels;
}

const DARK = "#0E1117";
const LAYOUT_BASE = {
  template: "plotly_dark" as const,
  paper_bgcolor: DARK,
  plot_bgcolor: DARK,
  font: { color: "#e0e0e0" },
  margin: { l: 50, r: 60, t: 40, b: 40 },
  legend: { orientation: "h" as const, y: 1.05, x: 0 },
  xaxis: { gridcolor: "rgba(255,255,255,0.05)" },
  yaxis: { gridcolor: "rgba(255,255,255,0.05)" },
};

export default function PriceTab({ rows, ticker, chartType, showMA, showBB, levels }: Props) {
  const dates  = rows.map(r => r.date);
  const opens  = rows.map(r => r.open);
  const highs  = rows.map(r => r.high);
  const lows   = rows.map(r => r.low);
  const closes = rows.map(r => r.close);
  const vols   = rows.map(r => r.volume);

  const volColors = rows.map((r, i) =>
    i === 0 || (r.close ?? 0) >= (r.open ?? 0) ? "#00C853" : "#FF1744"
  );

  const priceTrace = chartType === "Candlestick"
    ? {
        type: "candlestick" as const,
        x: dates, open: opens, high: highs, low: lows, close: closes,
        name: "Price",
        increasing: { line: { color: "#00C853" } },
        decreasing: { line: { color: "#FF1744" } },
        xaxis: "x", yaxis: "y",
      }
    : {
        type: "scatter" as const,
        x: dates, y: closes,
        mode: "lines" as const,
        name: "Close",
        line: { color: "#FF6B35", width: 2 },
        xaxis: "x", yaxis: "y",
      };

  const traces: object[] = [priceTrace];

  if (showMA) {
    const maColors: [keyof OHLCVRow, string][] = [
      ["sma20", "#00BCD4"], ["sma50", "#FFC107"], ["sma200", "#E040FB"],
    ];
    maColors.forEach(([key, color]) => {
      if (rows.some(r => r[key] != null)) {
        traces.push({
          type: "scatter", x: dates, y: rows.map(r => r[key]),
          mode: "lines", name: key.toUpperCase(),
          line: { color, width: 1.2, dash: "dot" },
          xaxis: "x", yaxis: "y",
        });
      }
    });
  }

  if (showBB && rows.some(r => r.bb_upper != null)) {
    traces.push({
      type: "scatter", x: dates, y: rows.map(r => r.bb_upper),
      mode: "lines", name: "BB Upper",
      line: { color: "rgba(128,128,255,0.5)", width: 1 },
      xaxis: "x", yaxis: "y",
    });
    traces.push({
      type: "scatter", x: dates, y: rows.map(r => r.bb_lower),
      mode: "lines", name: "BB Lower",
      line: { color: "rgba(128,128,255,0.5)", width: 1 },
      fill: "tonexty", fillcolor: "rgba(128,128,255,0.07)",
      xaxis: "x", yaxis: "y",
    });
  }

  // Volume
  traces.push({
    type: "bar", x: dates, y: vols, name: "Volume",
    marker: { color: volColors }, showlegend: false,
    xaxis: "x", yaxis: "y2",
  });
  if (rows.some(r => r.vol_sma20 != null)) {
    traces.push({
      type: "scatter", x: dates, y: rows.map(r => r.vol_sma20),
      mode: "lines", name: "Vol SMA20",
      line: { color: "#FFC107", width: 1.2 },
      xaxis: "x", yaxis: "y2",
    });
  }

  // RSI
  if (rows.some(r => r.rsi != null)) {
    traces.push({
      type: "scatter", x: dates, y: rows.map(r => r.rsi),
      mode: "lines", name: "RSI",
      line: { color: "#FF6B35", width: 1.5 },
      xaxis: "x", yaxis: "y3",
    });
  }

  // SL + target lines via shapes/annotations
  const shapes: object[] = [];
  const annotations: object[] = [];

  if (levels) {
    const addLine = (y: number, color: string, label: string, dash = "dash") => {
      shapes.push({ type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: y, y1: y,
                    line: { color, width: 1.5, dash } });
      annotations.push({ xref: "paper", x: 1.01, yref: "y", y, text: label,
                         showarrow: false, xanchor: "left", font: { color, size: 10 } });
    };
    addLine(levels.stop_loss, "#FF1744", `SL ₹${levels.stop_loss.toLocaleString("en-IN", {maximumFractionDigits:2})}`);
    const tColors = ["#66BB6A", "#00C853", "#1DE9B6"];
    Object.entries(levels.targets).forEach(([label, price], i) => {
      addLine(price, tColors[i] ?? "#00C853",
              `T${i+1} ₹${price.toLocaleString("en-IN", {maximumFractionDigits:2})}`, "dot");
    });
  }

  const layout = {
    ...LAYOUT_BASE,
    height: 650,
    title: { text: `${ticker}`, font: { size: 14 } },
    xaxis: { gridcolor: "rgba(255,255,255,0.05)", rangeslider: { visible: false } },
    yaxis:  { domain: [0.45, 1],   gridcolor: "rgba(255,255,255,0.05)", title: "Price" },
    yaxis2: { domain: [0.22, 0.42], gridcolor: "rgba(255,255,255,0.05)", title: "Vol" },
    yaxis3: { domain: [0, 0.19],    gridcolor: "rgba(255,255,255,0.05)", title: "RSI", range: [0, 100] },
    shapes,
    annotations,
  };

  return (
    <Plot
      data={traces as Plotly.Data[]}
      layout={layout as unknown as Partial<Plotly.Layout>}
      config={{ responsive: true, displayModeBar: true }}
      style={{ width: "100%", height: 650 }}
      useResizeHandler
    />
  );
}
