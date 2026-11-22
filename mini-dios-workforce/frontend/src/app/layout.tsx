import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mini-DIOS Plastics | Deterministic CP-SAT Plastic Factory OS",
  description:
    "Decision Intelligence Operating System for Plastic Manufacturing (Injection, Blow Molding & Extrusion) powered by Google OR-Tools CP-SAT.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
        />
      </head>
      <body className="min-h-screen antialiased selection:bg-cyan-500/30 selection:text-cyan-100">
        {children}
      </body>
    </html>
  );
}
