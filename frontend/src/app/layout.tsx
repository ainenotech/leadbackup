import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AINeotechnology | Lead Outreach & Intelligence",
  description: "Executive multi-channel lead outreach, analytics telemetry, RAG auto-reply, and conversion intelligence platform.",
  icons: {
    icon: "/logo-dark.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-[#F8FAFC]">
      <body className="min-h-full bg-[#F8FAFC] text-[#0F172A] antialiased">
        {children}
      </body>
    </html>
  );
}
