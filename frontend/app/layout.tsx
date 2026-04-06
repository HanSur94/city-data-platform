import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Stadtdaten Aalen",
  description: "Stadtdaten Aalen — Karte und Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="de"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {children}
        <footer className="text-xs text-muted-foreground py-1 px-4 border-t bg-background shrink-0">
          Datenquellen: UBA, DWD, NVBW, PEGELONLINE, LUBW, BASt, Autobahn GmbH, SMARD, MaStR, OSM, BNetzA, Wegweiser Kommune, Statistik BW, Zensus 2022, BA | Datenlizenz Deutschland
        </footer>
      </body>
    </html>
  );
}
