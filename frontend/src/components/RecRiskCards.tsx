"use client";

import { useState } from "react";
import type { Recommendation, RiskScore } from "@/types";

interface Props {
  rec: Recommendation;
  risk: RiskScore;
}

export default function RecRiskCards({ rec, risk }: Props) {
  const [showRecFactors, setShowRecFactors] = useState(false);
  const [showRiskFactors, setShowRiskFactors] = useState(false);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {/* Recommendation */}
      <div
        className="rounded-xl p-4"
        style={{ background: "rgba(0,0,0,0.3)", border: `2px solid ${rec.color}` }}
      >
        <div className="text-xs text-gray-400 text-center mb-1">Overall Recommendation</div>
        <div className="text-3xl font-extrabold text-center tracking-widest" style={{ color: rec.color }}>
          {rec.recommendation}
        </div>
        <div className="text-xs text-gray-400 text-center mt-1">
          Confidence: {rec.confidence.toFixed(0)}% &nbsp;|&nbsp; Score: {rec.score}/{rec.max_score}
        </div>
        <button
          onClick={() => setShowRecFactors(!showRecFactors)}
          className="text-xs text-gray-500 hover:text-gray-300 w-full mt-2 text-center"
        >
          {showRecFactors ? "▲ Hide" : "▼ View"} scoring factors
        </button>
        {showRecFactors && (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left py-1">Factor</th>
                  <th className="text-center">Signal</th>
                  <th className="text-center">Pts</th>
                </tr>
              </thead>
              <tbody>
                {rec.factors.map((f, i) => (
                  <tr key={i} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                    <td className="py-1 text-gray-300">{f.Factor}</td>
                    <td className="text-center">
                      <SignalPill signal={f.Signal as string} />
                    </td>
                    <td className="text-center text-gray-400">{f.Points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Risk */}
      <div
        className="rounded-xl p-4"
        style={{ background: "rgba(0,0,0,0.3)", border: `2px solid ${risk.color}` }}
      >
        <div className="text-xs text-gray-400 text-center mb-1">Risk Score</div>
        <div className="text-3xl font-extrabold text-center" style={{ color: risk.color }}>
          {risk.level === "HIGH" ? "🔴" : risk.level === "MEDIUM" ? "🟡" : "🟢"} {risk.level}
        </div>
        <div className="text-xs text-gray-400 text-center mt-1">
          Risk Index: {risk.pct.toFixed(0)} / 100
        </div>
        <button
          onClick={() => setShowRiskFactors(!showRiskFactors)}
          className="text-xs text-gray-500 hover:text-gray-300 w-full mt-2 text-center"
        >
          {showRiskFactors ? "▲ Hide" : "▼ View"} risk breakdown
        </button>
        {showRiskFactors && (
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left py-1">Factor</th>
                  <th className="text-left">Detail</th>
                  <th className="text-center">Risk</th>
                </tr>
              </thead>
              <tbody>
                {risk.factors.map((f, i) => (
                  <tr key={i} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                    <td className="py-1 text-gray-300 pr-2">{f.Factor}</td>
                    <td className="text-gray-400 pr-2">{f.Detail}</td>
                    <td className="text-center">
                      <span style={{
                        color: f.Risk === "High" ? "#FF1744" : f.Risk === "Medium" ? "#FFC107" : "#00C853"
                      }}>{f.Risk}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function SignalPill({ signal }: { signal: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    BUY:  { bg: "#00C853", text: "white" },
    SELL: { bg: "#FF1744", text: "white" },
    HOLD: { bg: "#FFC107", text: "black" },
  };
  const c = colors[signal] ?? { bg: "#555", text: "white" };
  return (
    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
          style={{ background: c.bg, color: c.text }}>
      {signal}
    </span>
  );
}
