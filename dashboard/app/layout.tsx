import type { Metadata } from "next";
import { IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import type { ReactElement, ReactNode } from "react";

import "./globals.css";

const titleFont = Space_Grotesk({
  variable: "--font-title",
  subsets: ["latin"]
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"]
});

export const metadata: Metadata = {
  title: "CDI Technician Dashboard",
  description: "Local dashboard for drive scan, NVMe self-test, and health metrics"
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>): ReactElement {
  return (
    <html lang="en">
      <body className={`${titleFont.variable} ${monoFont.variable} min-h-screen`}>{children}</body>
    </html>
  );
}
