import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "bonsai — traceable deep research",
  description: "Multi-agent deep research system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
