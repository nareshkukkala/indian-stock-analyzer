export function fmtCurrency(val: number | null | undefined, sym = "₹"): string {
  if (val == null) return "N/A";
  if (val >= 1e12) return `${sym}${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9)  return `${sym}${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e7)  return `${sym}${(val / 1e7).toFixed(2)}Cr`;
  if (val >= 1e5)  return `${sym}${(val / 1e5).toFixed(2)}L`;
  return `${sym}${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtNum(val: number | null | undefined, decimals = 2): string {
  if (val == null) return "N/A";
  return val.toFixed(decimals);
}

export function fmtPct(val: number | null | undefined): string {
  if (val == null) return "N/A";
  return `${(val * 100).toFixed(2)}%`;
}

export function fmtDivYield(val: number | null | undefined): string {
  if (val == null) return "N/A";
  // yfinance 1.x returns % directly (0.39 = 0.39%) if val < 1, else already a %
  return val >= 1 ? `${val.toFixed(2)}%` : `${(val * 100).toFixed(2)}%`;
}

export function fmtVolume(val: number | null | undefined): string {
  if (val == null) return "N/A";
  return val.toLocaleString("en-IN");
}

export function currencySymbol(currency: string | null | undefined): string {
  if (!currency) return "₹";
  if (currency.toUpperCase() === "INR") return "₹";
  return currency + " ";
}
