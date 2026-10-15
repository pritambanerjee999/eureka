/**
 * Root layout: applies global fonts, styles, and metadata for the Next.js app.
 *
 * @author Pritam
 * @date 2026-10-12
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@livekit/components-styles";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Eureka — Voice Physics Tutor",
  description: "Learn physics through conversation, Feynman style.",
};

/**
 * Wraps every page in the Inter font and the shared HTML shell.
 *
 * @param props - Component props.
 * @param props.children - The page content to render inside the body.
 * @returns The full HTML document shell.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
