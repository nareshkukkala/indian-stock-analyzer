import type { Fundamentals } from "@/types";
import { fmtCurrency, fmtNum, fmtPct, fmtDivYield, fmtVolume } from "@/lib/formatters";

interface Props {
  fundamentals: Fundamentals | null;
  loading: boolean;
}

function Metric({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="rounded-lg p-3"
         style={{ background: "#1E1E2E", border: "1px solid rgba(255,255,255,0.08)" }}
         title={help}>
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-base font-bold text-white mt-0.5">{value}</div>
    </div>
  );
}

export default function FundamentalsTab({ fundamentals: f, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400 mt-4">
        <span className="animate-spin">⏳</span> Loading fundamentals…
      </div>
    );
  }
  if (!f) {
    return <div className="text-gray-400 mt-4">No fundamental data available.</div>;
  }

  return (
    <div className="space-y-5">
      <div className="text-lg font-semibold text-white">Fundamental Analysis</div>

      {/* Data quality warning */}
      {f.data_quality === "minimal" && (
        <div className="rounded-lg px-4 py-3 text-sm text-yellow-300"
             style={{ background: "rgba(255,193,7,0.1)", border: "1px solid rgba(255,193,7,0.3)" }}>
          ⚠️ Fundamental data could not be fully loaded from Yahoo Finance. Some values may be unavailable.
          Try refreshing the page.
        </div>
      )}
      {f.data_quality === "partial" && (
        <div className="rounded-lg px-4 py-3 text-sm text-blue-300"
             style={{ background: "rgba(33,150,243,0.08)", border: "1px solid rgba(33,150,243,0.2)" }}>
          ℹ️ Some metrics retrieved from financial statements (may differ slightly from displayed Yahoo Finance values).
        </div>
      )}

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Metric label="Market Cap"    value={fmtCurrency(f.market_cap)} />
        <Metric label="P/E Ratio"     value={fmtNum(f.trailing_pe)} help="Price-to-Earnings (trailing)" />
        <Metric label="Forward P/E"   value={fmtNum(f.forward_pe)} />
        <Metric label="P/B Ratio"     value={fmtNum(f.price_to_book)} help="Price-to-Book" />
        <Metric label="EPS (TTM)"     value={fmtNum(f.trailing_eps)} />
        <Metric label="Revenue"       value={fmtCurrency(f.total_revenue)} />
        <Metric label="Div. Yield"    value={fmtDivYield(f.dividend_yield)} />
        <Metric label="Beta"          value={fmtNum(f.beta)} />
        <Metric label="Profit Margin" value={fmtPct(f.profit_margins)} />
        <Metric label="52W High"      value={fmtNum(f.fifty_two_week_high)} />
        <Metric label="52W Low"       value={fmtNum(f.fifty_two_week_low)} />
        <Metric label="Avg Volume"    value={fmtVolume(f.average_volume)} />
      </div>

      {/* Valuation row */}
      {(f.trailing_pe || f.price_to_book || f.trailing_eps) && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="Trailing P/E" value={fmtNum(f.trailing_pe)} help="Lower = cheaper vs earnings" />
          <Metric label="Price/Book"   value={fmtNum(f.price_to_book)} help="< 1 = trading below book value" />
          <Metric label="EPS (TTM)"    value={fmtNum(f.trailing_eps)} help="Earnings per share, trailing 12 months" />
          <Metric label="Total Debt"   value={fmtCurrency(f.total_debt)} />
        </div>
      )}

      <hr style={{ borderColor: "rgba(255,255,255,0.08)" }} />

      {/* Company details */}
      <div className="rounded-xl p-4 space-y-3"
           style={{ background: "#1E1E2E", border: "1px solid rgba(255,255,255,0.08)" }}>
        <div className="text-sm font-semibold text-gray-300">Company Details</div>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-1.5">
            <Row label="Sector"     value={f.sector} />
            <Row label="Industry"   value={f.industry} />
            <Row label="Employees"  value={f.employees ? f.employees.toLocaleString("en-IN") : null} />
            <Row label="Country"    value={f.country} />
            <Row label="Exchange"   value={f.exchange} />
            <Row label="Currency"   value={f.currency} />
          </div>
          <div className="space-y-1.5">
            <Row label="Gross Margin"     value={fmtPct(f.gross_margins)} />
            <Row label="Operating Margin" value={fmtPct(f.operating_margins)} />
            <Row label="Profit Margin"    value={fmtPct(f.profit_margins)} />
            <Row label="ROE"              value={fmtPct(f.roe)} />
            <Row label="ROA"              value={fmtPct(f.roa)} />
            <Row label="Operating CF"     value={fmtCurrency(f.operating_cashflow)} />
          </div>
        </div>
        {f.summary && (
          <div>
            <div className="text-xs font-semibold text-gray-400 mb-1">About</div>
            <div className="text-xs text-gray-400 leading-relaxed"
                 style={{ background: "rgba(255,255,255,0.03)", borderRadius: 6, padding: "0.75rem" }}>
              {f.summary.length > 700 ? f.summary.slice(0, 700) + "…" : f.summary}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex gap-2">
      <span className="text-gray-400 min-w-[130px]">{label}:</span>
      <span className="text-gray-200">{value ?? "N/A"}</span>
    </div>
  );
}
