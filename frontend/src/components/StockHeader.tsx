import type { StockMeta } from "@/types";
import { fmtVolume } from "@/lib/formatters";

interface Props {
  meta: StockMeta;
  ticker: string;
  sym: string;
}

export default function StockHeader({ meta, ticker, sym }: Props) {
  const pos = meta.day_change >= 0;
  const color = pos ? "#00C853" : "#FF1744";

  return (
    <div
      className="rounded-xl p-4 flex flex-wrap gap-4 items-center justify-between"
      style={{ background: "#1E1E2E", border: "1px solid rgba(255,255,255,0.08)" }}
    >
      <div>
        <div className="text-xl font-bold text-white">{meta.long_name || ticker}</div>
        <div className="text-xs text-gray-400 mt-0.5">{ticker}</div>
      </div>

      <div className="flex gap-6 flex-wrap">
        <div>
          <div className="text-xs text-gray-400">Last Price</div>
          <div className="text-2xl font-bold" style={{ color: "#FF6B35" }}>
            {sym}{meta.last_close.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-sm font-medium" style={{ color }}>
            {pos ? "+" : ""}{sym}{meta.day_change.toFixed(2)} ({pos ? "+" : ""}{meta.day_change_pct.toFixed(2)}%)
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-0.5 text-sm">
          <div>
            <span className="text-gray-400">Open </span>
            <span>{sym}{meta.open.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
          </div>
          <div>
            <span className="text-gray-400">High </span>
            <span style={{ color: "#00C853" }}>{sym}{meta.high.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
          </div>
          <div>
            <span className="text-gray-400">Volume </span>
            <span>{fmtVolume(meta.volume)}</span>
          </div>
          <div>
            <span className="text-gray-400">Low </span>
            <span style={{ color: "#FF1744" }}>{sym}{meta.low.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
