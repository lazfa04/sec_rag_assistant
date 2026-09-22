import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEC Filing Assistant",
  description:
    "Ask natural-language questions about 10-K and 10-Q filings, grounded in retrieved source text.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#06040f]">{children}</body>
    </html>
  );
}
