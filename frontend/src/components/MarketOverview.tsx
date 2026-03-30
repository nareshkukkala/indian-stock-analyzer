"use client";

import useSWR from "swr";
import { api, keys } from "@/lib/api";

export default function MarketOverview() {
  const { data } = useSWR(keys.market(), api.market, {
    refreshInterval: 60_000,
    revalidateOnFocus: false,
  });

  if (!data) return null;

  return (
    <div className="flex gap-3 overflow-x-auto flex-nowrap">
      {data.indices.map((idx) => {
        const pos = idx.change >= 0;
        return (
          <div key={idx.symbol} className="flex items-center gap-1.5 whitespace-nowrap">
            <span className="text-xs text-gray-400">{idx.name}</span>
            <span className="text-sm font-medium" style={{ color: "#e0e0e0" }}>
              {idx.price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
            </span>
            <span className="text-xs font-medium" style={{ color: pos ? "#00C853" : "#FF1744" }}>
              {pos ? "+" : ""}
              {idx.change_pct.toFixed(2)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
