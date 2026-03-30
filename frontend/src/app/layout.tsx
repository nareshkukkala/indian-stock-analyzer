import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Indian Stock Analyzer",
  description: "NSE/BSE stock analysis with technicals, fundamentals and AI recommendations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${geist.className} min-h-full`} style={{ background: "#0E1117", color: "#e0e0e0" }}>
        {children}
      </body>
    </html>
  );
}
